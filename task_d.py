from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from custom_topo import CustomTopo
import time
import os

# --- Setup Mininet with custom topology ---
topo = CustomTopo()
net = Mininet(topo=topo, controller=Controller, link=TCLink)
net.start()

# --- Hosts and DNS ---
host_objs = [net.get('H1'), net.get('H2'), net.get('H3'), net.get('H4')]
dns = net.get('dns')

# Start your custom DNS server in background
dns.cmd('python3 /home/mininet/dns-query-resolution/custom_dns.py &')
time.sleep(2)  # wait for DNS server to start

# Point all hosts to your custom DNS
for host in host_objs:
    host.cmd('echo "nameserver 10.0.0.5" > /etc/resolv.conf')

# --- Create temporary script for querying DNS inside hosts ---
temp_script_path = '/tmp/dns_query.py'
dns_query_code = """
from dnslib import DNSRecord, QTYPE
import sys

domain = sys.argv[1]
server = sys.argv[2]

try:
    q = DNSRecord.question(domain, qtype=QTYPE.A)
    resp_raw = q.send(server, 53, timeout=2)
    resp = DNSRecord.parse(resp_raw)
    if resp.a:
        print(resp.a.rdata)
except Exception as e:
    print('')
"""

# Write the script on all hosts
for host in host_objs + [dns]:
    host.cmd(f'echo "{dns_query_code}" > {temp_script_path}')

# --- Function to check DNS connectivity ---
def check_dns(host):
    result = host.cmd(f'python3 {temp_script_path} google.com 10.0.0.5')
    if result.strip():
        print(f"{host.name} is successfully using the custom DNS: {result.strip()}")
    else:
        print(f"{host.name} could NOT reach the custom DNS.")

# Run DNS check
for host in host_objs:
    check_dns(host)

# --- Function to resolve URL list from file ---
def resolve_urls_dnslib(host, url_file):
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    success = 0
    fail = 0
    total_time = 0.0

    for i, url in enumerate(urls, start=1):
        start = time.time()
        result = host.cmd(f'python3 {temp_script_path} {url} 10.0.0.5')
        latency = time.time() - start
        if result.strip():
            success += 1
            total_time += latency
        else:
            fail += 1

        # Checkpoint every 20 queries
        if i % 20 == 0:
            print(f"{host.name}: {i} queries processed...")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

# --- URL files ---
hosts_files = {
    'H1': '/home/mininet/dns-query-resolution/H1_urls.txt',
    'H2': '/home/mininet/dns-query-resolution/H2_urls.txt',
    'H3': '/home/mininet/dns-query-resolution/H3_urls.txt',
    'H4': '/home/mininet/dns-query-resolution/H4_urls.txt',
}

# --- Resolve URLs for each host ---
for hname, url_file in hosts_files.items():
    host = net.get(hname)
    print(f"\nResolving URLs for {hname} using custom DNS...")
    avg_latency, throughput, success, fail = resolve_urls_dnslib(host, url_file)
    print(f"{hname.upper()}:")
    print(f"Average Latency: {avg_latency:.3f} s")
    print(f"Throughput: {throughput:.2f} queries/sec")
    print(f"Successful: {success}, Failed: {fail}")

net.stop()
