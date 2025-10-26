from mininet.topo import Topo # to define the custom topology
from mininet.net import Mininet # to create and manage the network
from mininet.node import Controller, OVSSwitch # to specify controller and switch types
from mininet.cli import CLI # for interactive cli
from mininet.log import setLogLevel, info # for logging and debug info
from mininet.link import TCLink # for bandwidth/delay params

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
        self.addLink(h1, s1, bw = 100, delay = '2ms') # links
        self.addLink(h2, s2, bw = 100, delay = '2ms')
        self.addLink(h3, s3, bw = 100, delay = '2ms')
        self.addLink(h4, s4, bw = 100, delay = '2ms')
        self.addLink(s1, s2, bw = 100, delay = '5ms')
        self.addLink(s2, s3, bw = 100, delay = '8ms')
        self.addLink(s3, s4, bw = 100, delay = '10ms')
        self.addLink(dns, s2, bw = 100, delay = '1ms')

def run():
    topo = CustomTopo()
    net = Mininet(topo=topo, controller=Controller, switch=OVSSwitch, link=TCLink)
    net.start()
    info('*** Network started\n')
    net.pingAll() # testing connectivity
    CLI(net) # opening interactive CLI
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()