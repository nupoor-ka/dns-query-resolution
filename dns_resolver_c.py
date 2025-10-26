import socketserver
from dnslib import DNSRecord, QTYPE, RR, A
from collections import OrderedDict
import dns.resolver  # to forward queries

CACHE_LIMIT = 400
cache = OrderedDict()  # LRU cache: domain -> IP

UPSTREAM_DNS = '8.8.8.8'  # Can forward unresolved queries here
PORT = 53

class DNSHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data, sock = self.request
        request = DNSRecord.parse(data)
        qname = str(request.q.qname)
        qtype = QTYPE[request.q.qtype]
        
        print(f"Query: {qname} Type: {qtype}")
        
        # Only handle A records
        if qtype != "A":
            reply = request.reply()
            sock.sendto(reply.pack(), self.client_address)
            return
        
        # Check cache
        if qname in cache:
            ip = cache[qname]
            print("Cache HIT")
        else:
            print("Cache MISS")
            try:
                # Forward query to upstream DNS
                answer = dns.resolver.resolve(qname, 'A')
                ip = answer[0].to_text()
                # Add to cache
                cache[qname] = ip
                # Enforce cache limit
                if len(cache) > CACHE_LIMIT:
                    cache.popitem(last=False)  # Remove oldest
            except Exception as e:
                print(f"Failed to resolve {qname}: {e}")
                ip = None
        
        reply = request.reply()
        if ip:
            reply.add_answer(RR(qname, QTYPE.A, rdata=A(ip), ttl=300))
        sock.sendto(reply.pack(), self.client_address)

if __name__ == "__main__":
    print("Starting Custom DNS Resolver on port 53")
    server = socketserver.UDPServer(("", PORT), DNSHandler)
    server.serve_forever()
