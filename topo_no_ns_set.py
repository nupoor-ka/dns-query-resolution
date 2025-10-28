from mininet.topo import Topo #this defines the custom topology
from mininet.net import Mininet #this creates and manages the network
from mininet.node import Controller, OVSSwitch #this specifies controller and switch types
from mininet.cli import CLI #used for interactive cli
from mininet.log import setLogLevel, info #used for logging and debug info
from mininet.link import TCLink #used for bandwidth or delay params
from mininet.nodelib import NAT #to connect to the internet
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
        h2 = self.addHost('h2', ip = "10.0.0.2/24") # 24 is like the prefix length
        h3 = self.addHost('h3', ip = "10.0.0.3/24") 
        h4 = self.addHost('h4', ip = "10.0.0.4/24") #remaining bits will be used to identify indie hosts
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

def run():
    topo = CustomTopo()
    net = Mininet(topo=topo, controller=Controller, switch=OVSSwitch, link=TCLink) 
    net.start()
    info('*** Network started\n')
    hosts = [net.get('h1'), net.get('h2'), net.get('h3'), net.get('h4')]
    nat_ip = "10.0.0.6"
    info('Setting default routes for hosts to use NAT gateway\n')
    for host in hosts:
        info(f'Setting default route for {host.name} to {nat_ip}\n')
        host.cmd('ip route add default via %s' % nat_ip)
    net.get('dns').cmd('ip route add default via %s' % nat_ip)
    CLI(net)
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()
