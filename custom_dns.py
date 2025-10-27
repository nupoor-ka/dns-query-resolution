import socket
import time
import csv
from dnslib import DNSRecord, DNSHeader, DNSQuestion, QTYPE, RR, A
from collections import OrderedDict

# config
LISTEN_IP = "10.0.0.5"  # DNS server IP
LISTEN_PORT = 53 # dns goes through this port, udp
CACHE_LIMIT = 400 # 400 rn, not a
ROOT_SERVERS = ["198.41.0.4", "170.247.170.2", "192.33.4.12", "199.7.91.13",
                "192.203.230.10", "192.5.5.241", "192.112.36.4", "198.97.190.53",
                "192.36.148.17", "192.58.128.30", "193.0.14.129", "199.7.83.42",
                "202.12.27.33"]
LOG_FILE = "/home/mininet/dns-query-resolution/dns_log.csv"

class LRUCache: # lru jic
    def __init__(self, capacity):
        self.cache = OrderedDict()
        self.capacity = capacity

    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key) # cool
            return self.cache[key]
        return None

    def put(self, key, value):
        self.cache[key] = value
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

cache = LRUCache(CACHE_LIMIT) # init cache

csv_file = open(LOG_FILE, 'w', newline='')
csv_writer = csv.DictWriter(csv_file, fieldnames=[ # from the question
    "timestamp","domain","resolution_mode","server_ip",
    "step","response","rtt","total_time","cache_status"
])
csv_writer.writeheader()

def query_server(domain, server_ip):
    q = DNSRecord.question(domain) # creating the query with the domain name, asks for A type record
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # opening udp socket, af_inet - ipv4 addr family, sock_dgram - datagram mode
    s.settimeout(3) # will wait 3 seconds for reply
    start = time.time()
    try:
        s.sendto(q.pack(), (server_ip, 53)) # sending the created query packet converted to bytes to the server ip port 53
        data, _ = s.recvfrom(512) # conventionally max size is 512 bytes
        rtt = time.time() - start
        response = DNSRecord.parse(data) # parse converts from binary to human-readable
        return response, rtt
    except socket.timeout:
        return None, None
    finally:
        s.close() # closes socket in any case

def recursive_resolve(domain):
    log_entries = [] # list of dicts
    total_start = time.time()
    cached = cache.get(domain) # cache key if found else None
    if cached: # if found in cache
        total_time = time.time() - total_start
        log_entries.append({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "domain": domain,
            "resolution_mode": "Cache",
            "server_ip": "-",
            "step": "Cache",
            "response": cached,
            "rtt": 0,
            "total_time": total_time,
            "cache_status": "HIT"
        })
        return cached, log_entries
    current_servers = ROOT_SERVERS.copy() # didn't find domain name in cache, start looking from root servers
    response_ip = None
    for step_name in ["Root", "TLD", "Authoritative"]:
        for server in current_servers: # going through all servers in this step
            resp, rtt = query_server(domain, server)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            if resp is None:
                continue  # try next server
            answer = resp.rr # found response, will get either next step servers or resolved ip
            if answer: # if found ip
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
                for entry in log_entries:
                    entry["total_time"] = round(total_time, 4)
                cache.put(domain, response_ip)
                return response_ip, log_entries
            additional = resp.ar # additional records - next step servers
            new_servers = [str(rr.rdata) for rr in additional if rr.rtype == QTYPE.A] # getting ip from the recs
            if new_servers:
                current_servers = new_servers
                log_entries.append({
                    "timestamp": timestamp,
                    "domain": domain,
                    "resolution_mode": "Recursive",
                    "server_ip": server,
                    "step": step_name,
                    "response": ",".join(new_servers), # comma separated list of 
                    "rtt": round(rtt, 4),
                    "total_time": 0,
                    "cache_status": "MISS"
                })
                break
        else:
            continue # else to the for server loop, done with servers in this step, move to the next
    total_time = time.time() - total_start
    for entry in log_entries:
        entry["total_time"] = round(total_time, 4)
    return response_ip, log_entries

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # udp socket, same thing as before
sock.bind((LISTEN_IP, LISTEN_PORT)) # listening at ip 10.0.0.5, port 53, could also put ip as 0.0.0.0 implying listen at all interfaces
print(f"dns server listening on {LISTEN_IP}:{LISTEN_PORT}")
try:
    while True: # continuously listening
        data, addr = sock.recvfrom(512) # whatever you received 
        request = DNSRecord.parse(data)
        qname = str(request.q.qname).rstrip('.') # extra . at the end of domain name
        ip, logs = recursive_resolve(qname)
        for entry in logs:
            csv_writer.writerow(entry)
        csv_file.flush()
        reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q) # rd-recursion desired, ra-recursion available, qr-0 query 1 response, aa-authoritative answer
        if ip:
            try:
                reply.add_answer(RR(
                    rname=request.q.qname,
                    rtype=QTYPE.A,
                    rclass=1, # class 1 is internet, otherwise can be some archaic networks or none or any
                    ttl=60, # 60 seconds
                    rdata=A(ip) # ipv4 addr
                ))
            except Exception as e:
                print(f"error creating rr for {ip}: {e}")
        sock.sendto(reply.pack(), addr)

except KeyboardInterrupt:
    print("keyboard interrupt, shutting down dns server")

finally:
    csv_file.close() # closing csv file
    sock.close() # closing socket
