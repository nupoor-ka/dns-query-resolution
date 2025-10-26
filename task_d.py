from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from custom_topo import CustomTopo
import time

# --- Setup Mininet with custom topology ---
topo = CustomTopo()
net = Mininet(topo=topo, controller=Controller, link=TCLink)
net.start()

# --- Hosts and DNS ---
host_objs = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
dns = net.get('dns')

# Start your custom DNS server in background
dns.cmd('python3 /home/mininet/dns-query-resolution/custom_dns.py &')
time.sleep(2)  # wait for DNS server to start
output = dns.cmd('ps aux | grep custom_dns.py | grep -v grep')
if output.strip():
    print("[OK] custom_dns.py is running:")
    print(output)
else:
    print("[ERROR] custom_dns.py not found in process list!")
# --- Point all hosts to your custom DNS ---
for host in host_objs:
    host.cmd('sh -c "echo nameserver 10.0.0.5 > /etc/resolv.conf"')

# --- Function to check DNS connectivity using dig ---
def check_dns(host):
    result = host.cmd('dig @10.0.0.5 google.com +short')
    print(result)
    if result.strip():
        print(f"{host.name} is successfully using the custom DNS: {result.strip()}")
    else:
        print(f"{host.name} could NOT reach the custom DNS.")

# Run DNS check
for host in host_objs:
    check_dns(host)

# --- Function to resolve URLs from file using dig ---
def resolve_urls_dig(host, url_file):
    with open(url_file, 'r') as f:
        urls = [line.strip() for line in f if line.strip()]

    success = 0
    fail = 0
    total_time = 0.0

    for i, url in enumerate(urls, start=1):
        start = time.time()
        result = host.cmd(f'dig @10.0.0.5 {url} +short')
        latency = time.time() - start
        if result.strip():
            success += 1
            total_time += latency
        else:
            fail += 1

        if i % 20 == 0:
            print(f"{host.name}: {i} queries processed...")

    avg_latency = total_time / success if success else 0
    throughput = success / total_time if total_time > 0 else 0
    return avg_latency, throughput, success, fail

# --- URL files ---
hosts_files = {
    'h1': '/home/mininet/dns-query-resolution/H1_urls.txt',
    'h2': '/home/mininet/dns-query-resolution/H2_urls.txt',
    'h3': '/home/mininet/dns-query-resolution/H3_urls.txt',
    'h4': '/home/mininet/dns-query-resolution/H4_urls.txt',
}

# --- Resolve URLs for each host ---
for hname, url_file in hosts_files.items():
    host = net.get(hname)
    print(f"\nResolving URLs for {hname} using custom DNS...")
    avg_latency, throughput, success, fail = resolve_urls_dig(host, url_file)
    print(f"{hname.upper()}:")
    print(f"Average Latency: {avg_latency:.3f} s")
    print(f"Throughput: {throughput:.2f} queries/sec")
    print(f"Successful: {success}, Failed: {fail}")

net.stop()
