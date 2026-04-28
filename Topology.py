#!/usr/bin/env python3

import sys
import argparse
from mininet.net import Mininet
from mininet.node import OVSSwitch, RemoteController
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink


def topology6(controller_mode='none'):

    # Controller setup
    if controller_mode == 'none':
        net = Mininet(
            controller=None,
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=False
        )
    elif controller_mode == 'ryu':
        net = Mininet(
            controller=lambda name: RemoteController(
                name, ip='127.0.0.1', port=6633),
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=False
        )
    else:  # floodlight
        net = Mininet(
            controller=lambda name: RemoteController(
                name, ip='127.0.0.1', port=6653),
            switch=OVSSwitch,
            link=TCLink,
            autoSetMacs=False
        )

    info('*** Adding switches\n')
    s1 = net.addSwitch('s1', dpid='0000000000000001', failMode='secure')
    s2 = net.addSwitch('s2', dpid='0000000000000002', failMode='secure')
    s3 = net.addSwitch('s3', dpid='0000000000000003', failMode='secure')
    s4 = net.addSwitch('s4', dpid='0000000000000004', failMode='secure')
    s5 = net.addSwitch('s5', dpid='0000000000000005', failMode='secure')
    s6 = net.addSwitch('s6', dpid='0000000000000006', failMode='secure')
    s7 = net.addSwitch('s7', dpid='0000000000000007', failMode='secure')

    info('*** Adding hosts\n')
    h1 = net.addHost('h1', ip='10.0.1.1/24', mac='00:00:00:00:01:01')
    h2 = net.addHost('h2', ip='10.0.1.2/24', mac='00:00:00:00:01:02')
    h3 = net.addHost('h3', ip='10.0.2.1/24', mac='00:00:00:00:02:01')
    h4 = net.addHost('h4', ip='10.0.2.2/24', mac='00:00:00:00:02:02')
    h5 = net.addHost('h5', ip='10.0.3.1/24', mac='00:00:00:00:03:01')
    h6 = net.addHost('h6', ip='10.0.3.2/24', mac='00:00:00:00:03:02')
    h7 = net.addHost('h7', ip='10.0.4.1/24', mac='00:00:00:00:04:01')
    h8 = net.addHost('h8', ip='10.0.4.2/24', mac='00:00:00:00:04:02')

    info('*** Adding links\n')
    net.addLink(s1, s2)
    net.addLink(s1, s3)
    net.addLink(s2, s4)
    net.addLink(s2, s5)
    net.addLink(s3, s6)
    net.addLink(s3, s7)
    net.addLink(s4, h1)
    net.addLink(s4, h2)
    net.addLink(s5, h3)
    net.addLink(s5, h4)
    net.addLink(s6, h5)
    net.addLink(s6, h6)
    net.addLink(s7, h7)
    net.addLink(s7, h8)

    info('*** Starting network\n')
    net.build()

    if controller_mode == 'none':
        for sw in [s1, s2, s3, s4, s5, s6, s7]:
            sw.start([])
    else:
        c0 = net.addController('c0')
        for sw in [s1, s2, s3, s4, s5, s6, s7]:
            sw.start([c0])

     # Force OpenFlow 1.3
    import os
    for sw in net.switches:
        os.system('ovs-vsctl set bridge %s protocols=OpenFlow13' % sw.name)

    # ----------------------------------------------------------------
    # Static routes - automatically added so hosts can reach
    # other subnets without manual route commands every time
    # ----------------------------------------------------------------
    info('*** Adding static routes\n')

    # H1, H2 -> 10.0.3.x (H5,H6) and 10.0.2.x (H3,H4)
    h1.cmd('ip route add 10.0.3.0/24 dev h1-eth0')
    h1.cmd('ip route add 10.0.2.0/24 dev h1-eth0')
    h1.cmd('ip route add 10.0.4.0/24 dev h1-eth0')
    h2.cmd('ip route add 10.0.3.0/24 dev h2-eth0')
    h2.cmd('ip route add 10.0.2.0/24 dev h2-eth0')
    h2.cmd('ip route add 10.0.4.0/24 dev h2-eth0')

    # H3, H4 -> 10.0.3.x (H5,H6) and 10.0.1.x (H1,H2)
    h3.cmd('ip route add 10.0.3.0/24 dev h3-eth0')
    h3.cmd('ip route add 10.0.1.0/24 dev h3-eth0')
    h3.cmd('ip route add 10.0.4.0/24 dev h3-eth0')
    h4.cmd('ip route add 10.0.3.0/24 dev h4-eth0')
    h4.cmd('ip route add 10.0.1.0/24 dev h4-eth0')
    h4.cmd('ip route add 10.0.4.0/24 dev h4-eth0')

    # H5, H6 -> 10.0.1.x and 10.0.2.x
    h5.cmd('ip route add 10.0.1.0/24 dev h5-eth0')
    h5.cmd('ip route add 10.0.2.0/24 dev h5-eth0')
    h5.cmd('ip route add 10.0.4.0/24 dev h5-eth0')
    h6.cmd('ip route add 10.0.1.0/24 dev h6-eth0')
    h6.cmd('ip route add 10.0.2.0/24 dev h6-eth0')
    h6.cmd('ip route add 10.0.4.0/24 dev h6-eth0')

    # H7, H8 -> each other only
    h7.cmd('ip route add 10.0.4.2/32 dev h7-eth0')
    h8.cmd('ip route add 10.0.4.1/32 dev h8-eth0')

    # H7, H8 only talk to each other - no extra routes needed

    info('*** Network is ready\n')
    info('*\n')
    info('*   H1=10.0.1.1  H2=10.0.1.2  (s4)\n')
    info('*   H3=10.0.2.1  H4=10.0.2.2  (s5)\n')
    info('*   H5=10.0.3.1  H6=10.0.3.2  (s6)\n')
    info('*   H7=10.0.4.1  H8=10.0.4.2  (s7)\n')
    info('*\n')
    info('*   Open Terminal 2 and run:  sudo bash AddRules.sh\n')
    info('*   Then run:                 pingall\n')
    info('*\n')

    CLI(net)

    info('*** Stopping network\n')
    net.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--controller',
                        choices=['none', 'ryu', 'floodlight'],
                        default='none')
    args = parser.parse_args()
    setLogLevel('info')
    topology6(controller_mode=args.controller)
