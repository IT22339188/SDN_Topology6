#!/usr/bin/env python3
"""
IE4080 - Software Defined Networks
Assignment 2 - Part C
Topology 6 - Floodlight Flow Installer

POLICY:
  ALLOW : H1,H2,H3,H4  ->  H5,H6
  ALLOW : H5,H6         ->  H1,H2   ONLY
  ALLOW : H7  <->  H8
  DENY  : H1,H2,H3,H4  ->  H7,H8
  DENY  : H5,H6         ->  H3,H4  (initiation blocked via ICMP type trick)
  DENY  : H7,H8         ->  anyone else

KEY DESIGN - ICMP stateless reply trick (s6):
  icmp_type=8 = echo REQUEST  (H5 initiating to H3 - BLOCK, priority 200)
  icmp_type=0 = echo REPLY    (H5 replying to H3  - ALLOW, priority 300)

HOW TO RUN:
  Terminal 1: cd ~/floodlight && sudo java -jar ~/floodlight.jar
  Terminal 2: sudo mn -c && sudo python3 Topology.py --controller floodlight
  Terminal 3: sudo python3 AddRulesFloodlight.py
  Terminal 2: mininet> pingall
"""

import requests
import json
import sys
import time

FLOODLIGHT_IP = '127.0.0.1'
FLOODLIGHT_PORT = 8080
BASE_URL = f'http://{FLOODLIGHT_IP}:{FLOODLIGHT_PORT}'
STATIC_FLOW_URL = f'{BASE_URL}/wm/staticflowpusher/json'
CLEAR_URL = f'{BASE_URL}/wm/staticflowpusher/clear/all/json'

# Switch DPIDs (Floodlight uses hex format)
DPID = {
    's1': '00:00:00:00:00:00:00:01',
    's2': '00:00:00:00:00:00:00:02',
    's3': '00:00:00:00:00:00:00:03',
    's4': '00:00:00:00:00:00:00:04',
    's5': '00:00:00:00:00:00:00:05',
    's6': '00:00:00:00:00:00:00:06',
    's7': '00:00:00:00:00:00:00:07',
}

flow_counter = 0


def check_floodlight():
    try:
        r = requests.get(f'{BASE_URL}/wm/core/controller/summary/json', timeout=3)
        if r.status_code == 200:
            print('[OK] Floodlight is running!')
            return True
        else:
            print('ERROR: Floodlight returned status', r.status_code)
            return False
    except Exception as e:
        print('ERROR: Floodlight controller is not running!')
        print('  Start it with: cd ~/floodlight && sudo java -jar ~/floodlight.jar')
        return False


def clear_all_flows():
    try:
        r = requests.delete(CLEAR_URL, timeout=5)
        print('[OK] Cleared all existing flows')
    except Exception as e:
        print('WARNING: Could not clear flows:', e)


def push_flow(name, switch, priority, match, actions):
    global flow_counter
    flow_counter += 1
    flow = {
        'switch': DPID[switch],
        'name': f'{switch}_{name}_{flow_counter}',
        'priority': str(priority),
        'active': 'true',
    }
    flow.update(match)
    flow.update(actions)

    try:
        r = requests.post(
            STATIC_FLOW_URL,
            data=json.dumps(flow),
            headers={'Content-Type': 'application/json'},
            timeout=5)
        if r.status_code != 200:
            print(f'  WARNING: Flow push failed for {flow["name"]}: {r.text}')
    except Exception as e:
        print(f'  ERROR pushing flow {flow["name"]}: {e}')


def arp_allow(switch, in_port, out_ports, priority=500):
    if not out_ports:
        push_flow('arp_drop', switch, priority,
                  {'eth_type': '0x0806', 'in_port': str(in_port)},
                  {'actions': 'drop'})
    else:
        actions = ','.join([f'output={p}' for p in out_ports])
        push_flow('arp', switch, priority,
                  {'eth_type': '0x0806', 'in_port': str(in_port)},
                  {'actions': actions})


def ip_allow(switch, priority, match, out_port):
    match['eth_type'] = '0x0800'
    push_flow('allow', switch, priority, match,
              {'actions': f'output={out_port}'})


def ip_drop(switch, priority, match):
    match['eth_type'] = '0x0800'
    push_flow('drop', switch, priority, match,
              {'actions': 'drop'})


def icmp_allow(switch, priority, in_port, src, dst, icmp_type, out_port):
    push_flow('icmp_allow', switch, priority,
              {
                  'eth_type': '0x0800',
                  'ip_proto': '0x01',
                  'in_port': str(in_port),
                  'ipv4_src': src,
                  'ipv4_dst': dst,
                  'icmpv4_type': str(icmp_type),
              },
              {'actions': f'output={out_port}'})


def default_drop(switch):
    push_flow('default_drop', switch, 1,
              {},
              {'actions': 'drop'})


# ============================================================
# S1: port1=s2  port2=s3  (Core)
# ============================================================
def install_s1():
    print('  Installing s1 (Core)...')
    sw = 's1'

    # ARP
    arp_allow(sw, 1, [2])
    arp_allow(sw, 2, [1])

    # ALLOW: h1,h2 -> h5,h6
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.1.0/24', 'ipv4_dst': '10.0.3.0/24'}, 2)
    # ALLOW: h3,h4 -> h5,h6
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.2.0/24', 'ipv4_dst': '10.0.3.0/24'}, 2)
    # ALLOW: h5,h6 -> h1,h2
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.1.0/24'}, 1)
    # ALLOW: h5,h6 reply -> h3,h4
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.2.0/24'}, 1)

    # BLOCK: -> h7,h8
    ip_drop(sw, 200, {'ipv4_dst': '10.0.4.0/24'})
    # BLOCK: h7,h8 ->
    ip_drop(sw, 200, {'ipv4_src': '10.0.4.0/24'})

    default_drop(sw)
    print('  [OK] s1 done')


# ============================================================
# S2: port1=s1  port2=s4(H1,H2)  port3=s5(H3,H4)
# ============================================================
def install_s2():
    print('  Installing s2 (Distribution-Left)...')
    sw = 's2'

    # ARP
    arp_allow(sw, 1, [2, 3])
    arp_allow(sw, 2, [1])
    arp_allow(sw, 3, [1])

    # ALLOW: h1,h2 -> h5,h6
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.1.0/24', 'ipv4_dst': '10.0.3.0/24'}, 1)
    # ALLOW: h3,h4 -> h5,h6
    ip_allow(sw, 100, {'in_port': '3', 'ipv4_src': '10.0.2.0/24', 'ipv4_dst': '10.0.3.0/24'}, 1)
    # ALLOW: h5,h6 -> h1,h2
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.1.0/24'}, 2)
    # ALLOW: h5,h6 reply -> h3,h4
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.2.0/24'}, 3)

    # BLOCK: -> h7,h8
    ip_drop(sw, 200, {'ipv4_dst': '10.0.4.0/24'})

    default_drop(sw)
    print('  [OK] s2 done')


# ============================================================
# S3: port1=s1  port2=s6(H5,H6)  port3=s7(H7,H8)
# ============================================================
def install_s3():
    print('  Installing s3 (Distribution-Right)...')
    sw = 's3'

    # ARP: s1 <-> s6 only, block s7
    arp_allow(sw, 1, [2])
    arp_allow(sw, 2, [1])
    arp_allow(sw, 3, [])  # drop

    # ALLOW: h1,h2 -> h5,h6
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.1.0/24', 'ipv4_dst': '10.0.3.0/24'}, 2)
    # ALLOW: h3,h4 -> h5,h6
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.2.0/24', 'ipv4_dst': '10.0.3.0/24'}, 2)
    # ALLOW: h5,h6 -> h1,h2
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.1.0/24'}, 1)
    # ALLOW: h5,h6 reply -> h3,h4
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.2.0/24'}, 1)

    # BLOCK: h5,h6 -> h7,h8
    ip_drop(sw, 200, {'in_port': '2', 'ipv4_dst': '10.0.4.0/24'})
    # BLOCK: h7,h8 -> outside
    ip_drop(sw, 200, {'in_port': '3', 'ipv4_src': '10.0.4.0/24'})
    # BLOCK: outside -> h7,h8
    ip_drop(sw, 200, {'ipv4_dst': '10.0.4.0/24'})

    default_drop(sw)
    print('  [OK] s3 done')


# ============================================================
# S4: port1=s2  port2=h1  port3=h2
# ============================================================
def install_s4():
    print('  Installing s4 (Access - H1,H2)...')
    sw = 's4'

    # ARP
    arp_allow(sw, 1, [2, 3])
    arp_allow(sw, 2, [1])
    arp_allow(sw, 3, [1])

    # ALLOW: h1 -> h5,h6
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.1.1', 'ipv4_dst': '10.0.3.0/24'}, 1)
    # ALLOW: h2 -> h5,h6
    ip_allow(sw, 100, {'in_port': '3', 'ipv4_src': '10.0.1.2', 'ipv4_dst': '10.0.3.0/24'}, 1)
    # ALLOW: h5,h6 -> h1
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.1.1'}, 2)
    # ALLOW: h5,h6 -> h2
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.1.2'}, 3)

    # BLOCK: -> h7,h8
    ip_drop(sw, 200, {'ipv4_dst': '10.0.4.0/24'})

    default_drop(sw)
    print('  [OK] s4 done')


# ============================================================
# S5: port1=s2  port2=h3  port3=h4
# ============================================================
def install_s5():
    print('  Installing s5 (Access - H3,H4)...')
    sw = 's5'

    # ARP
    arp_allow(sw, 1, [2, 3])
    arp_allow(sw, 2, [1])
    arp_allow(sw, 3, [1])

    # ALLOW: h3 -> h5,h6
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.2.1', 'ipv4_dst': '10.0.3.0/24'}, 1)
    # ALLOW: h4 -> h5,h6
    ip_allow(sw, 100, {'in_port': '3', 'ipv4_src': '10.0.2.2', 'ipv4_dst': '10.0.3.0/24'}, 1)
    # ALLOW: h5,h6 reply -> h3
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.2.1'}, 2)
    # ALLOW: h5,h6 reply -> h4
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.3.0/24', 'ipv4_dst': '10.0.2.2'}, 3)

    # BLOCK: -> h7,h8
    ip_drop(sw, 200, {'ipv4_dst': '10.0.4.0/24'})

    default_drop(sw)
    print('  [OK] s5 done')


# ============================================================
# S6: port1=s3  port2=h5  port3=h6
# ICMP TRICK used here
# ============================================================
def install_s6():
    print('  Installing s6 (Access - H5,H6) with ICMP trick...')
    sw = 's6'

    # ARP
    arp_allow(sw, 1, [2, 3])
    arp_allow(sw, 2, [1])
    arp_allow(sw, 3, [1])

    # ALLOW: h5 -> h1,h2
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.3.1', 'ipv4_dst': '10.0.1.0/24'}, 1)
    # ALLOW: h6 -> h1,h2
    ip_allow(sw, 100, {'in_port': '3', 'ipv4_src': '10.0.3.2', 'ipv4_dst': '10.0.1.0/24'}, 1)

    # ALLOW: h1,h2 -> h5
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.1.0/24', 'ipv4_dst': '10.0.3.1'}, 2)
    # ALLOW: h1,h2 -> h6
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.1.0/24', 'ipv4_dst': '10.0.3.2'}, 3)
    # ALLOW: h3,h4 -> h5
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.2.0/24', 'ipv4_dst': '10.0.3.1'}, 2)
    # ALLOW: h3,h4 -> h6
    ip_allow(sw, 100, {'in_port': '1', 'ipv4_src': '10.0.2.0/24', 'ipv4_dst': '10.0.3.2'}, 3)

    # ICMP TRICK: ALLOW echo REPLY (type=0) from h5 -> h3,h4 (priority 300)
    icmp_allow(sw, 300, 2, '10.0.3.1', '10.0.2.0/24', 0, 1)
    # ICMP TRICK: ALLOW echo REPLY (type=0) from h6 -> h3,h4 (priority 300)
    icmp_allow(sw, 300, 3, '10.0.3.2', '10.0.2.0/24', 0, 1)

    # BLOCK: h5 initiating -> h3,h4 (priority 200)
    ip_drop(sw, 200, {'in_port': '2', 'ipv4_src': '10.0.3.1', 'ipv4_dst': '10.0.2.0/24'})
    # BLOCK: h6 initiating -> h3,h4
    ip_drop(sw, 200, {'in_port': '3', 'ipv4_src': '10.0.3.2', 'ipv4_dst': '10.0.2.0/24'})

    # BLOCK: h5,h6 -> h7,h8
    ip_drop(sw, 200, {'in_port': '2', 'ipv4_dst': '10.0.4.0/24'})
    ip_drop(sw, 200, {'in_port': '3', 'ipv4_dst': '10.0.4.0/24'})

    default_drop(sw)
    print('  [OK] s6 done')


# ============================================================
# S7: port1=s3  port2=h7  port3=h8  (ISOLATED)
# ============================================================
def install_s7():
    print('  Installing s7 (Access - H7,H8 ISOLATED)...')
    sw = 's7'

    # ARP: only h7 <-> h8, block uplink
    arp_allow(sw, 1, [])  # drop
    arp_allow(sw, 2, [3])
    arp_allow(sw, 3, [2])

    # ALLOW: h7 -> h8
    ip_allow(sw, 100, {'in_port': '2', 'ipv4_src': '10.0.4.1', 'ipv4_dst': '10.0.4.2'}, 3)
    # ALLOW: h8 -> h7
    ip_allow(sw, 100, {'in_port': '3', 'ipv4_src': '10.0.4.2', 'ipv4_dst': '10.0.4.1'}, 2)

    # BLOCK: uplink -> h7,h8
    ip_drop(sw, 200, {'in_port': '1'})
    # BLOCK: h7 -> outside
    ip_drop(sw, 200, {'in_port': '2', 'ipv4_src': '10.0.4.1', 'ipv4_dst': '10.0.1.0/24'})
    ip_drop(sw, 200, {'in_port': '2', 'ipv4_src': '10.0.4.1', 'ipv4_dst': '10.0.2.0/24'})
    ip_drop(sw, 200, {'in_port': '2', 'ipv4_src': '10.0.4.1', 'ipv4_dst': '10.0.3.0/24'})
    # BLOCK: h8 -> outside
    ip_drop(sw, 200, {'in_port': '3', 'ipv4_src': '10.0.4.2', 'ipv4_dst': '10.0.1.0/24'})
    ip_drop(sw, 200, {'in_port': '3', 'ipv4_src': '10.0.4.2', 'ipv4_dst': '10.0.2.0/24'})
    ip_drop(sw, 200, {'in_port': '3', 'ipv4_src': '10.0.4.2', 'ipv4_dst': '10.0.3.0/24'})

    default_drop(sw)
    print('  [OK] s7 done')


# ============================================================
# Main
# ============================================================
def main():
    print('=' * 60)
    print('  Topology 6 - Floodlight Flow Installer')
    print('=' * 60)

    if not check_floodlight():
        sys.exit(1)

    print('\n[1] Clearing all existing flows...')
    clear_all_flows()
    time.sleep(1)

    print('\n[2] Installing flows on all switches...')
    install_s1()
    install_s2()
    install_s3()
    install_s4()
    install_s5()
    install_s6()
    install_s7()

    print('\n' + '=' * 60)
    print('  All flows installed successfully!')
    print('=' * 60)
    print('\nExpected pingall result:')
    print('  h1 -> X X X h5 h6 X X')
    print('  h2 -> X X X h5 h6 X X')
    print('  h3 -> X X X h5 h6 X X')
    print('  h4 -> X X X h5 h6 X X')
    print('  h5 -> h1 h2 X X X X X')
    print('  h6 -> h1 h2 X X X X X')
    print('  h7 -> X X X X X X h8')
    print('  h8 -> X X X X X X h7')
    print('=' * 60)


if __name__ == '__main__':
    main()
