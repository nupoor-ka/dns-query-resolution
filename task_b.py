from mininet.net import Mininet
from mininet.node import Controller
from mininet.link import TCLink
from mininet.cli import CLI
from url_resolver_default import resolve_urls
from custom_topo import CustomTopo

topo = CustomTopo()
net = Mininet(topo=topo, controller=Controller, link=TCLink)
net.start()

# List of host objects
host_objs = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]

for host in host_objs:
    host.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')

hosts = {
    'h1': '/home/mininet/dns-query-resolution/H1_urls.txt',
    'h2': '/home/mininet/dns-query-resolution/H2_urls.txt',
    'h3': '/home/mininet/dns-query-resolution/H3_urls.txt',
    'h4': '/home/mininet/dns-query-resolution/H4_urls.txt',
}

for hname, url_file in hosts.items():
    print(f"Reading for {hname}")
    host = net.get(hname)
    print(f"Received {hname}")
    avg_latency, throughput, success, fail = resolve_urls(host, url_file)
    print(f"\n=== {hname.upper()} ===")
    print(f"Average Latency: {avg_latency:.3f} s")
    print(f"Throughput: {throughput:.2f} queries/sec")
    print(f"Successful: {success}%, Failed: {fail}%")

net.stop()
