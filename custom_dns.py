import socket
import time
import csv
from dnslib import DNSRecord, DNSHeader, DNSQuestion, QTYPE, RR
from collections import OrderedDict

LISTEN_IP = "0.0.0.0" #to listen on all interfaces
LISTEN_PORT = 53
CACHE_LIMIT = 400
ROOT_SERVERS = [
    "198.41.0.4", "199.9.14.201", "192.33.4.12", "199.7.91.13",
    "192.203.230.10", "192.5.5.241", "192.112.36.4", "198.97.190.53",
    "192.36.148.17", "192.58.128.30", "193.0.14.129", "199.7.83.42",
    "202.12.27.33"
]
LOG_FILE = "/home/mininet/dns-query-resolution/dns_log.csv"

#Least recently used cache

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

csv_file = open(LOG_FILE, 'w', newline='')
csv_writer = csv.DictWriter(csv_file, fieldnames=[
    "timestamp","domain","resolution_mode","server_ip",
    "step","response","rtt","total_time","cache_status"
])
csv_writer.writeheader()

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

def recursive_resolve(domain):
    #Full recursive resolution: Root, TLD, Authoritative
    log_entries = []
    total_start = time.time()

    cached = cache.get(domain) # checking cache
    if cached:
        total_time = time.time() - total_start
        log_entries.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "domain": domain,
            "resolution_mode": "Cache",
            "server_ip": "-",
            "step": "Cache",
            "response_or_referral": cached,
            "rtt": 0,
            "total_time": total_time,
            "cache_status": "HIT"
        })
        return cached, log_entries

    #if MISS thrn recursive resolution
    current_servers = ROOT_SERVERS.copy()
    response_ip = None

    for step_name in ["Root", "TLD", "Authoritative"]:
        for server in current_servers:
            resp, rtt = query_server(domain, server)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if resp is None:
                continue  # try next server
            answer = resp.rr # will be ip, if auth server, else none
            if answer: #found ip, was at auth sever ie
                response_ip = str(answer[0].rdata)
                log_entries.append({
                    "timestamp": timestamp,
                    "domain": domain,
                    "resolution_mode": "Recursive",
                    "server_ip": server,
                    "step": step_name,
                    "response": response_ip,
                    "rtt": round(rtt, 4),
                    "total_time": 0,  # will update later
                    "cache_status": "MISS"
                })
                total_time = time.time() - total_start
                # Update log total_time
                for entry in log_entries:
                    entry["total_time"] = round(total_time, 4)
                # Cache it
                cache.put(domain, response_ip)
                return response_ip, log_entries
            # didn't find ip
            authority = resp.auth # list of servers to check in next step
            additional = resp.ar # list of ip addresses of those servers
            new_servers = []
            for rr in additional:
                if rr.rtype == QTYPE.A:
                    new_servers.append(str(rr.rdata))
            if new_servers:
                current_servers = new_servers #looking at next step now
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
        else:
            continue
    total_time = time.time() - total_start
    for entry in log_entries:
        entry["total_time"] = round(total_time, 4)
    return response_ip, log_entries
#udp stuff
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))
print(f"DNS server listening on {LISTEN_IP}:{LISTEN_PORT}")

try:
    while True:
        data, addr = sock.recvfrom(512) # max 512 bytes, random cap
        request = DNSRecord.parse(data)
        qname = str(request.q.qname)
        qname = qname.rstrip('.')  # remove trailing dot
        ip, logs = recursive_resolve(qname)
        for entry in logs:
            csv_writer.writerow(entry)
        csv_file.flush()
        if ip:
            reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)
            reply.add_answer(RR(rname=request.q.qname, rtype=QTYPE.A, rclass=1, ttl=60, rdata=ip))
            sock.sendto(reply.pack(), addr)
        else:
            reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)
            sock.sendto(reply.pack(), addr)
except KeyboardInterrupt:
    print("keyboard interrupt")
finally:
    csv_file.close()
    sock.close()
