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
        h1 = self.addHost('h1', ip = "10.0.0.1/24") # hosts
        h2 = self.addHost('h2', ip = "10.0.0.2/24") # have to add ip addr in cidr notation - classless inter-domain routing
        h3 = self.addHost('h3', ip = "10.0.0.3/24") # ip/prefix len
        h4 = self.addHost('h4', ip = "10.0.0.4/24") # prefix len - same local network indicator, remaining bits will be used to identify indie hosts
        dns = self.addHost('dns', ip = "10.0.0.5/24") # dns resolver
        s1 = self.addSwitch('s1') # switches
        s2 = self.addSwitch('s2')
        s3 = self.addSwitch('s3')
        s4 = self.addSwitch('s4')
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

# ... (imports and CustomTopo definition) ...

def run():
    topo = CustomTopo()
    # Ensure you are passing the NAT class to Mininet for proper initialization
    net = Mininet(topo=topo, controller=Controller, switch=OVSSwitch, link=TCLink, host=NAT) 
    
    net.start()
    info('*** Network started\n')

    # Get a list of your regular hosts (excluding the NAT node)
    hosts = net.hosts[:-2] # Assuming DNS_Resolver is the second-to-last and nat is the last node
                           # Better: use net.get('H1'), net.get('H2'), etc.

    nat_ip = "10.0.0.6" # The internal IP of the NAT node

    info('*** Setting default routes for hosts to use NAT gateway\n')
    for host in hosts:
        info(f'Setting default route for {host.name} to {nat_ip}\n')
        # This command sets the default route for each host
        host.cmd('ip route add default via %s' % nat_ip) 
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
    ########################
    for host in hosts:
        host.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    #########################
    # If you want the 'DNS Resolver' host to have internet access too:
    net.get('dns').cmd('ip route add default via %s' % nat_ip)

    # Note: If your hosts still can't resolve public DNS names, 
    # you may need to manually set their DNS server to a public one like 8.8.8.8:
    # for host in hosts:
    #     host.cmd('echo "nameserver 8.8.8.8" > /etc/resolv.conf')
    
    info('*** Testing connectivity to the internet (e.g., pinging Google DNS)\n')
    # Try pinging a public IP from H1
    h1 = net.get('h1')
    h1.cmd('ping -c 3 8.8.8.8') 

    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()