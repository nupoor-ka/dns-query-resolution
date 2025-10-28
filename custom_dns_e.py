import socket
import time
import csv
from dnslib import DNSRecord, DNSHeader, QTYPE, RR, A
from collections import OrderedDict

# ------------------- Configuration -------------------
LISTEN_IP = "10.0.0.5"
LISTEN_PORT = 53
CACHE_LIMIT = 400
ROOT_SERVERS = [
    "198.41.0.4", "170.247.170.2", "192.33.4.12", "199.7.91.13",
    "192.203.230.10", "192.5.5.241", "192.112.36.4", "198.97.190.53",
    "192.36.148.17", "192.58.128.30", "193.0.14.129", "199.7.83.42",
    "202.12.27.33"
]
LOG_FILE = "/home/mininet/dns-query-resolution/dns_log_e.csv"

# ------------------- LRU Cache -------------------
class LRUCache:
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

cache = LRUCache(CACHE_LIMIT)

# ------------------- CSV Setup -------------------
csv_file = open(LOG_FILE, 'w', newline='')
csv_writer = csv.DictWriter(csv_file, fieldnames=[
    "timestamp", "domain", "resolution_mode", "server_ip",
    "step", "response", "rtt", "total_time", "cache_status"
])
csv_writer.writeheader()

# ------------------- Query Helper -------------------
def query_server(domain, server_ip):
    q = DNSRecord.question(domain)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    start = time.time()
    try:
        s.sendto(q.pack(), (server_ip, 53))
        data, _ = s.recvfrom(512)
        rtt = time.time() - start
        response = DNSRecord.parse(data)
        return response, rtt
    except socket.timeout:
        return None, None
    finally:
        s.close()

# ------------------- Recursive Resolver -------------------
def recursive_resolve(domain):
    log_entries = []
    total_start = time.time()
    cached = cache.get(domain)
    if cached:
        total_time = time.time() - total_start
        log_entries.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "domain": domain,
            "resolution_mode": "Recursive",
            "server_ip": "-",
            "step": "Cache",
            "response": cached,
            "rtt": 0,
            "total_time": round(total_time, 4),
            "cache_status": "HIT"
        })
        return cached, log_entries

    current_servers = ROOT_SERVERS.copy()
    response_ip = None

    for step_name in ["Root", "TLD", "Authoritative"]:
        for server in current_servers:
            resp, rtt = query_server(domain, server)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

            if resp is None:
                continue

            # Found final answer
            if resp.rr:
                response_ip = str(resp.rr[0].rdata)
                log_entries.append({
                    "timestamp": timestamp,
                    "domain": domain,
                    "resolution_mode": "Recursive",
                    "server_ip": server,
                    "step": step_name,
                    "response": response_ip,
                    "rtt": round(rtt, 4),
                    "total_time": 0,
                    "cache_status": "MISS"
                })
                total_time = time.time() - total_start
                for entry in log_entries:
                    entry["total_time"] = round(total_time, 4)
                cache.put(domain, response_ip)
                return response_ip, log_entries

            additional = resp.ar
            new_servers = [str(rr.rdata) for rr in additional if rr.rtype == QTYPE.A]
            if new_servers:
                current_servers = new_servers
                log_entries.append({
                    "timestamp": timestamp,
                    "domain": domain,
                    "resolution_mode": "Recursive",
                    "server_ip": server,
                    "step": step_name,
                    "response": ",".join(new_servers),
                    "rtt": round(rtt, 4),
                    "total_time": 0,
                    "cache_status": "MISS"
                })
                break

    total_time = time.time() - total_start
    for entry in log_entries:
        entry["total_time"] = round(total_time, 4)
    return response_ip, log_entries

# ------------------- Main Server -------------------
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))
print(f"[+] Custom DNS Server listening on {LISTEN_IP}:{LISTEN_PORT}")

try:
    while True:
        data, addr = sock.recvfrom(512)
        request = DNSRecord.parse(data)
        qname = str(request.q.qname).rstrip('.')

        recursion_requested = bool(request.header.rd)
        print(f"[+] Received query for {qname}, RD={recursion_requested}")

        if recursion_requested:
            ip, logs = recursive_resolve(qname)
            mode = "Recursive"
        else:
            ip = cache.get(qname)
            logs = [{
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "domain": qname,
                "resolution_mode": "Non-Recursive",
                "server_ip": "-",
                "step": "Cache",
                "response": ip if ip else "N/A",
                "rtt": 0,
                "total_time": 0,
                "cache_status": "HIT" if ip else "MISS"
            }]
            mode = "Non-Recursive"

        for entry in logs:
            csv_writer.writerow(entry)
        csv_file.flush()

        reply = DNSRecord(
            DNSHeader(
                id=request.header.id,
                qr=1,
                aa=1,
                ra=1,
                rd=recursion_requested
            ),
            q=request.q
        )

        if ip:
            reply.add_answer(RR(
                rname=request.q.qname,
                rtype=QTYPE.A,
                rclass=1,
                ttl=60,
                rdata=A(ip)
            ))

        sock.sendto(reply.pack(), addr)

except KeyboardInterrupt:
    print("\n[!] DNS server shutting down...")
finally:
    csv_file.close()
    sock.close()
