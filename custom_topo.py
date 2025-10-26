from mininet.topo import Topo # to define the custom topology
from mininet.net import Mininet # to create and manage the network
from mininet.node import Controller, OVSSwitch # to specify controller and switch types
from mininet.cli import CLI # for interactive cli
from mininet.log import setLogLevel, info # for logging and debug info
from mininet.link import TCLink # for bandwidth/delay params
from mininet.nodelib import NAT
"""
H1: 10.0.0.1, H1 - S1 100Mbps, 2ms delay
H2: 10.0.0.2, H2 - S2 100Mbps, 2ms delay
H3: 10.0.0.3, H3 - S3 100Mbps, 2ms delay
H4: 10.0.0.4, H4 - S4 100Mbps, 2ms delay
S1 - S2 100 Mbps, 5ms delay
S2 - S3 100 Mbps, 8ms delay
S3 - S4 100 Mbps, 10ms delay
DNS resolver - 10.0.0.5
S2 - DNS resolver 100 Mbps, 5ms delay
"""

class CustomTopo(Topo):
    def build(self):
        h1 = self.addHost('H1', ip = "10.0.0.1/24") # hosts
        h2 = self.addHost('H2', ip = "10.0.0.2/24") # have to add ip addr in cidr notation - classless inter-domain routing
        h3 = self.addHost('H3', ip = "10.0.0.3/24") # ip/prefix len
        h4 = self.addHost('H4', ip = "10.0.0.4/24") # prefix len - same local network indicator, remaining bits will be used to identify indie hosts
        dns = self.addHost('DNS Resolver', ip = "10.0.0.5/24") # dns resolver
        s1 = self.addSwitch('S1') # switches
        s2 = self.addSwitch('S2')
        s3 = self.addSwitch('S3')
        s4 = self.addSwitch('S4')
        nat= self.addNode('nat', cls=NAT, ip='10.0.0.6/24', inNamespace=False)
        self.addLink(h1, s1, bw = 100, delay = '2ms') # links
        self.addLink(h2, s2, bw = 100, delay = '2ms')
        self.addLink(h3, s3, bw = 100, delay = '2ms')
        self.addLink(h4, s4, bw = 100, delay = '2ms')
        self.addLink(s1, s2, bw = 100, delay = '5ms')
        self.addLink(s2, s3, bw = 100, delay = '8ms')
        self.addLink(s3, s4, bw = 100, delay = '10ms')
        self.addLink(dns, s2, bw = 100, delay = '1ms')
        self.addLink(nat, s2)

def run():
    topo = CustomTopo()
    # Use default Host class. The 'nat' node uses the NAT class from the topo definition.
    net = Mininet(topo=topo, controller=Controller, switch=OVSSwitch, link=TCLink, host=Host)
    net.start()
    info('*** Network started and NAT initialized.\n')

    nat_ip = "10.0.0.6"       # IP of the NAT gateway
    resolver_ip = "10.0.0.5"  # IP of your custom DNS Resolver host

    # 1. Configure the CUSTOM DNS RESOLVER HOST (10.0.0.5)
    dns_resolver_host = net.get('DNS_Resolver')
    
    # Resolver needs a route to the internet (via NAT)
    info(f'*** Configuring DNS Resolver ({resolver_ip}): Gateway={nat_ip}\n')
    dns_resolver_host.cmd(f'ip route add default via {nat_ip}')
    
    # Resolver needs to know which public server to use for lookups
    # This is the "internet" side of its DNS function
    dns_resolver_host.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    
    # 2. Configure ALL OTHER HOSTS (H1, H2, H3, H4)
    # They route via NAT but use 10.0.0.5 for DNS.
    hosts_to_configure = [net.get(f'H{i}') for i in range(1, 5)]

    info(f'*** Configuring H1-H4: Gateway={nat_ip}, DNS={resolver_ip}\n')
    for host in hosts_to_configure:
        # Set default route to the NAT node
        host.cmd(f'ip route add default via {nat_ip}') 
        
        # CRITICAL: Set the DNS server to your custom DNS Resolver (10.0.0.5)
        host.cmd(f'echo "nameserver {resolver_ip}" > /etc/resolv.conf')
        
    info('\n*** Configuration complete. Testing internet connectivity (via custom DNS)...\n')
    
    h1 = net.get('H1')
    
    # Test 1: Ping IP (Tests routing via NAT)
    ip_ping_result = h1.cmd('ping -c 2 8.8.8.8')
    info(f'H1 Ping 8.8.8.8 result (Routing Test):\n{ip_ping_result}')

    # Test 2: Dig a public URL (Tests DNS via 10.0.0.5 -> NAT -> Internet)
    # This is the specific query path your task requires!
    dns_dig_result = h1.cmd('dig +time=5 +tries=1 +short google.com')
    info(f'H1 Dig google.com result (DNS Path Test):\n{dns_dig_result}\n')
    
    if "google.com" in dns_dig_result:
        info("SUCCESS: DNS resolution via 10.0.0.5 is working.\n")
    else:
        info("WARNING: DNS resolution failed. Check the NAT and DNS_Resolver configuration.\n")

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()