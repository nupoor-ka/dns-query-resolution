import socket, time, csv
from dnslib import DNSRecord, DNSHeader, QTYPE, RR, A
from collections import OrderedDict

LISTEN_IP = "10.0.0.5"
LISTEN_PORT = 53
CACHE_LIMIT = 400
ROOT_SERVERS = ["198.41.0.4","170.247.170.2","192.33.4.12","199.7.91.13","192.203.230.10","192.5.5.241","192.112.36.4","198.97.190.53","192.36.148.17","192.58.128.30","193.0.14.129","199.7.83.42","202.12.27.33"]
LOG_FILE = "/home/mininet/dns-query-resolution/dns_custom_10.csv"

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
csv_writer = csv.DictWriter(csv_file, fieldnames=["timestamp","domain","resolution_mode","server_ip","step","response","rtt","total_time","cache_status","servers_visited"])
csv_writer.writeheader()

def query_server(domain, server_ip):
    q = DNSRecord.question(domain)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    start = time.time()
    try:
        print(f"[>] Querying {server_ip} for {domain}")
        s.sendto(q.pack(), (server_ip, 53))
        data, _ = s.recvfrom(512)
        rtt = time.time() - start
        resp = DNSRecord.parse(data)
        print(f"[<] Response from {server_ip} in {rtt:.3f}s")
        return resp, rtt
    except socket.timeout:
        print(f"[x] Timeout {server_ip}")
        return None, None
    finally:
        s.close()

def recursive_resolve(domain):
    print(f"\n=== Resolving {domain} ===")
    log_entries, servers_visited = [], 0
    total_start = time.time()
    cached = cache.get(domain)
    if cached:
        total_time = time.time() - total_start
        print(f"[CACHE HIT] {domain} → {cached}")
        log_entries.append({"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"domain":domain,"resolution_mode":"Cache","server_ip":"-","step":"Cache","response":cached,"rtt":0,"total_time":round(total_time,4),"cache_status":"HIT","servers_visited":0})
        return cached, log_entries
    current_servers = ROOT_SERVERS.copy()
    response_ip = None
    for step_name in ["Root","TLD","Authoritative"]:
        print(f"\n--- {step_name} ---")
        for server in current_servers:
            servers_visited += 1
            resp, rtt = query_server(domain, server)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if resp is None:
                continue
            answers, additionals = resp.rr, resp.ar
            if answers:
                response_ip = str(answers[0].rdata)
                print(f"[✓] {domain} resolved by {server} ({step_name}) → {response_ip}")
                total_time = time.time() - total_start
                log_entries.append({"timestamp":timestamp,"domain":domain,"resolution_mode":"Recursive","server_ip":server,"step":step_name,"response":response_ip,"rtt":round(rtt,4),"total_time":round(total_time,4),"cache_status":"MISS","servers_visited":servers_visited})
                cache.put(domain, response_ip)
                return response_ip, log_entries
            new_servers = [str(rr.rdata) for rr in additionals if rr.rtype == QTYPE.A]
            if new_servers:
                print(f"[>] {server} referred to {len(new_servers)}: {', '.join(new_servers)}")
                log_entries.append({"timestamp":timestamp,"domain":domain,"resolution_mode":"Recursive","server_ip":server,"step":step_name,"response":",".join(new_servers),"rtt":round(rtt,4),"total_time":0,"cache_status":"MISS","servers_visited":servers_visited})
                current_servers = new_servers
                break
    print(f"[!] Failed to resolve {domain}")
    total_time = time.time() - total_start
    for e in log_entries: e["total_time"]=round(total_time,4)
    return response_ip, log_entries

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LISTEN_IP, LISTEN_PORT))
print(f"DNS server listening on {LISTEN_IP}:{LISTEN_PORT}")

try:
    while True:
        data, addr = sock.recvfrom(512)
        request = DNSRecord.parse(data)
        qname = str(request.q.qname).rstrip('.')
        ip, logs = recursive_resolve(qname)
        for e in logs: csv_writer.writerow(e)
        csv_file.flush()
        reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)
        if ip:
            try:
                reply.add_answer(RR(rname=request.q.qname,rtype=QTYPE.A,rclass=1,ttl=60,rdata=A(ip)))
            except Exception as ex:
                print(f"[!] Error creating RR for {ip}: {ex}")
        sock.sendto(reply.pack(), addr)
except KeyboardInterrupt:
    print("\nShutting down")
finally:
    csv_file.close()
    sock.close()
