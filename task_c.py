from mininet.net import Mininet 
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from url_resolver_default import resolve_urls
from custom_topo import CustomTopo
from dnslib import DNSRecord, QTYPE
import time

topo = CustomTopo()
net = Mininet(topo=topo, controller=Controller, link=TCLink)
net.start()

# List of host objects
host_objs = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
dns = net.get('dns')

# Start your custom DNS server
dns.cmd('python3 /home/mininet/dns-query-resolution/custom_dns.py &')
time.sleep(2)  # give DNS server time to start

# Point all hosts to your custom DNS
for host in host_objs:
    host.cmd('echo "nameserver 10.0.0.5" > /etc/resolv.conf')

# Check connectivity using dnslib instead of dig
def check_dns(host):
    try:
        request = DNSRecord.question("google.com", qtype=QTYPE.A)
        # Execute the query inside the host namespace
        response_raw = host.cmd(f'python3 -c "from dnslib import DNSRecord, QTYPE; import sys; r=DNSRecord.question(\'google.com\', qtype=QTYPE.A); resp=DNSRecord.parse(r.send(\'10.0.0.5\',53,timeout=2)); print(resp.a.rdata)"')
        if response_raw.strip():
            print(f"{host.name} is successfully using the custom DNS: {response_raw.strip()}")
        else:
            print(f"{host.name} could NOT reach the custom DNS.")
    except Exception as e:
        print(f"Error querying DNS from {host.name}: {e}")

for host in host_objs:
    check_dns(host)

# Now resolve URLs from files using dnslib directly for speed
def resolve_urls_dnslib(host, url_file):
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    success = 0
    fail = 0
    total_time = 0.0

    for i, url in enumerate(urls, start=1):
        start = time.time()
        try:
            request = DNSRecord.question(url, qtype=QTYPE.A)
            response_raw = host.cmd(f'python3 -c "from dnslib import DNSRecord, QTYPE; import sys; r=DNSRecord.question(\'{url}\', qtype=QTYPE.A); resp=DNSRecord.parse(r.send(\'10.0.0.5\',53,timeout=2)); print(resp.a.rdata if resp.a else \'\')"')
            latency = time.time() - start
            if response_raw.strip():
                success += 1
                total_time += latency
            else:
                fail += 1
        except Exception as e:
            fail += 1
            latency = time.time() - start

        # Print checkpoint every 20 queries
        if i % 20 == 0:
            print(f"{host.name}: {i} queries processed...")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

hosts_files = {
    'h1': '/home/mininet/dns-query-resolution/H1_urls.txt',
    'h2': '/home/mininet/dns-query-resolution/H2_urls.txt',
    'h3': '/home/mininet/dns-query-resolution/H3_urls.txt',
    'h4': '/home/mininet/dns-query-resolution/H4_urls.txt',
}

for hname, url_file in hosts_files.items():
    host = net.get(hname)
    print(f"Resolving URLs for {hname} using dnslib...")
    avg_latency, throughput, success, fail = resolve_urls_dnslib(host, url_file)
    print(f"\n{hname.upper()}")
    print(f"Average Latency: {avg_latency:.3f} s")
    print(f"Throughput: {throughput:.2f} queries/sec")
    print(f"Successful: {success}, Failed: {fail}")

net.stop()
