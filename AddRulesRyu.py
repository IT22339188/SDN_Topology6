"""
IE4080 - Software Defined Networks
Assignment 2 - Part B
Topology 6 - Proactive Ryu Controller

POLICY:
  ALLOW : H1,H2,H3,H4  ->  H5,H6
  ALLOW : H5,H6         ->  H1,H2   ONLY
  ALLOW : H7  <->  H8
  DENY  : H1,H2,H3,H4  ->  H7,H8
  DENY  : H5,H6         ->  H3,H4  (initiation blocked via ICMP type trick)
  DENY  : H7,H8         ->  anyone else

KEY DESIGN - ICMP stateless reply trick (s6):
  OpenFlow 1.3 has no connection tracking.
  icmp_type=8 = echo REQUEST  (H5 initiating to H3 - BLOCK)
  icmp_type=0 = echo REPLY    (H5 replying to H3  - ALLOW, priority 300)

PORT MAP:
  s1 : eth1=s2    eth2=s3
  s2 : eth1=s1    eth2=s4    eth3=s5
  s3 : eth1=s1    eth2=s6    eth3=s7
  s4 : eth1=s2    eth2=h1    eth3=h2
  s5 : eth1=s2    eth2=h3    eth3=h4
  s6 : eth1=s3    eth2=h5    eth3=h6
  s7 : eth1=s3    eth2=h7    eth3=h8

HOW TO RUN:
  Terminal 1: ryu-manager AddRulesRyu.py
  Terminal 2: sudo mn -c && sudo python3 Topology.py --controller ryu
  Terminal 2: mininet> pingall
"""

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib import hub
import logging

LOG = logging.getLogger('AddRulesRyu')

DPID_NAMES = {
    1: 's1 (Core)',
    2: 's2 (Distribution-Left)',
    3: 's3 (Distribution-Right)',
    4: 's4 - H1,H2',
    5: 's5 - H3,H4',
    6: 's6 - H5,H6',
    7: 's7 - H7,H8',
}


class Topology6Ryu(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(Topology6Ryu, self).__init__(*args, **kwargs)
        self.installed = set()
        self.datapaths = {}
        LOG.info("Topology6 Ryu Controller started...")
        self.monitor_thread = hub.spawn(self._monitor_ports)

    # =========================================================
    # Helpers
    # =========================================================
    def get_port_no(self, dp, intf_name):
        for port_no, port in dp.ports.items():
            if port.name.decode('utf-8') == intf_name:
                return port_no
        return None

    def add_flow(self, dp, priority, match, actions):
        ofp = dp.ofproto
        parser = dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=dp, priority=priority, match=match,
            instructions=inst, idle_timeout=0, hard_timeout=0)
        dp.send_msg(mod)

    def drop_flow(self, dp, priority, match):
        mod = dp.ofproto_parser.OFPFlowMod(
            datapath=dp, priority=priority, match=match,
            instructions=[], idle_timeout=0, hard_timeout=0)
        dp.send_msg(mod)

    def ip_allow(self, dp, priority, in_port, src, dst, out_port):
        parser = dp.ofproto_parser
        match = parser.OFPMatch(
            in_port=in_port, eth_type=0x0800,
            ipv4_src=src, ipv4_dst=dst)
        self.add_flow(dp, priority, match, [parser.OFPActionOutput(out_port)])

    def ip_drop(self, dp, priority, match_kwargs):
        parser = dp.ofproto_parser
        match_kwargs['eth_type'] = 0x0800
        match = parser.OFPMatch(**match_kwargs)
        self.drop_flow(dp, priority, match)

    def icmp_allow(self, dp, priority, in_port, src, dst, icmp_type, out_port):
        """Allow ICMP with specific type."""
        parser = dp.ofproto_parser
        match = parser.OFPMatch(
            in_port=in_port, eth_type=0x0800,
            ip_proto=1,  # ICMP
            ipv4_src=src, ipv4_dst=dst,
            icmpv4_type=icmp_type)
        self.add_flow(dp, priority, match, [parser.OFPActionOutput(out_port)])

    def arp_flow(self, dp, priority, in_port, out_ports):
        parser = dp.ofproto_parser
        match = parser.OFPMatch(eth_type=0x0806, in_port=in_port)
        if out_ports:
            actions = [parser.OFPActionOutput(p) for p in out_ports]
            self.add_flow(dp, priority, match, actions)
        else:
            self.drop_flow(dp, priority, match)

    # =========================================================
    # Switch connect
    # =========================================================
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, ev):
        dp = ev.msg.datapath
        self.datapaths[dp.id] = dp
        LOG.info("Switch connected: %s", DPID_NAMES.get(dp.id, dp.id))
        req = dp.ofproto_parser.OFPPortDescStatsRequest(dp, 0)
        dp.send_msg(req)
        self._try_install_rules(dp)

    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_reply_handler(self, ev):
        dp = ev.msg.datapath
        if dp.id not in self.installed:
            self._try_install_rules(dp)

    @set_ev_cls(ofp_event.EventOFPPortStatus, CONFIG_DISPATCHER)
    def port_status_handler(self, ev):
        dp = ev.msg.datapath
        if ev.msg.reason == dp.ofproto.OFPPR_ADD and dp.id not in self.installed:
            self._try_install_rules(dp)

    def _monitor_ports(self):
        while True:
            hub.sleep(2)
            for dpid, dp in list(self.datapaths.items()):
                if dpid not in self.installed:
                    self._try_install_rules(dp)

    def _try_install_rules(self, dp):
        dpid = dp.id
        parser = dp.ofproto_parser

        if dpid in self.installed:
            return True

        port_names = {
            1: ['s1-eth1', 's1-eth2'],
            2: ['s2-eth1', 's2-eth2', 's2-eth3'],
            3: ['s3-eth1', 's3-eth2', 's3-eth3'],
            4: ['s4-eth1', 's4-eth2', 's4-eth3'],
            5: ['s5-eth1', 's5-eth2', 's5-eth3'],
            6: ['s6-eth1', 's6-eth2', 's6-eth3'],
            7: ['s7-eth1', 's7-eth2', 's7-eth3'],
        }

        p = {}
        for intf in port_names.get(dpid, []):
            no = self.get_port_no(dp, intf)
            if no:
                p[intf] = no

        if len(p) < len(port_names.get(dpid, [])):
            LOG.warning("Missing ports for dpid=%s, will retry...", dpid)
            return False

        # Default DROP
        self.drop_flow(dp, 1, parser.OFPMatch())

        if dpid == 1:
            self.install_s1(dp, p)
        elif dpid == 2:
            self.install_s2(dp, p)
        elif dpid == 3:
            self.install_s3(dp, p)
        elif dpid == 4:
            self.install_s4(dp, p)
        elif dpid == 5:
            self.install_s5(dp, p)
        elif dpid == 6:
            self.install_s6(dp, p)
        elif dpid == 7:
            self.install_s7(dp, p)

        self.installed.add(dpid)
        LOG.info("Rules installed: %s", DPID_NAMES.get(dpid, dpid))
        return True

    # =========================================================
    # s1: eth1=s2  eth2=s3   (Core)
    # =========================================================
    def install_s1(self, dp, p):
        e1 = p['s1-eth1']  # s2 side (h1-h4)
        e2 = p['s1-eth2']  # s3 side (h5-h8)

        # ARP
        self.arp_flow(dp, 500, e1, [e2])
        self.arp_flow(dp, 500, e2, [e1])

        # ALLOW: h1,h2 -> h5,h6
        self.ip_allow(dp, 100, e1, ('10.0.1.0', '255.255.255.0'), ('10.0.3.0', '255.255.255.0'), e2)
        # ALLOW: h3,h4 -> h5,h6
        self.ip_allow(dp, 100, e1, ('10.0.2.0', '255.255.255.0'), ('10.0.3.0', '255.255.255.0'), e2)
        # ALLOW: h5,h6 -> h1,h2
        self.ip_allow(dp, 100, e2, ('10.0.3.0', '255.255.255.0'), ('10.0.1.0', '255.255.255.0'), e1)
        # ALLOW: h5,h6 reply -> h3,h4
        self.ip_allow(dp, 100, e2, ('10.0.3.0', '255.255.255.0'), ('10.0.2.0', '255.255.255.0'), e1)

        # BLOCK: -> h7,h8
        self.ip_drop(dp, 200, {'ipv4_dst': ('10.0.4.0', '255.255.255.0')})
        # BLOCK: h7,h8 ->
        self.ip_drop(dp, 200, {'ipv4_src': ('10.0.4.0', '255.255.255.0')})

    # =========================================================
    # s2: eth1=s1  eth2=s4(H1,H2)  eth3=s5(H3,H4)
    # =========================================================
    def install_s2(self, dp, p):
        e1 = p['s2-eth1']  # s1
        e2 = p['s2-eth2']  # s4 (h1,h2)
        e3 = p['s2-eth3']  # s5 (h3,h4)

        # ARP
        self.arp_flow(dp, 500, e1, [e2, e3])
        self.arp_flow(dp, 500, e2, [e1])
        self.arp_flow(dp, 500, e3, [e1])

        # ALLOW: h1,h2 -> h5,h6
        self.ip_allow(dp, 100, e2, ('10.0.1.0', '255.255.255.0'), ('10.0.3.0', '255.255.255.0'), e1)
        # ALLOW: h3,h4 -> h5,h6
        self.ip_allow(dp, 100, e3, ('10.0.2.0', '255.255.255.0'), ('10.0.3.0', '255.255.255.0'), e1)
        # ALLOW: h5,h6 -> h1,h2
        self.ip_allow(dp, 100, e1, ('10.0.3.0', '255.255.255.0'), ('10.0.1.0', '255.255.255.0'), e2)
        # ALLOW: h5,h6 reply -> h3,h4
        self.ip_allow(dp, 100, e1, ('10.0.3.0', '255.255.255.0'), ('10.0.2.0', '255.255.255.0'), e3)

        # BLOCK: -> h7,h8
        self.ip_drop(dp, 200, {'ipv4_dst': ('10.0.4.0', '255.255.255.0')})

    # =========================================================
    # s3: eth1=s1  eth2=s6(H5,H6)  eth3=s7(H7,H8)
    # =========================================================
    def install_s3(self, dp, p):
        e1 = p['s3-eth1']  # s1
        e2 = p['s3-eth2']  # s6 (h5,h6)
        e3 = p['s3-eth3']  # s7 (h7,h8)

        # ARP: s1 <-> s6 only, block s7
        self.arp_flow(dp, 500, e1, [e2])
        self.arp_flow(dp, 500, e2, [e1])
        self.arp_flow(dp, 500, e3, [])  # drop

        # ALLOW: h1,h2 -> h5,h6
        self.ip_allow(dp, 100, e1, ('10.0.1.0', '255.255.255.0'), ('10.0.3.0', '255.255.255.0'), e2)
        # ALLOW: h3,h4 -> h5,h6
        self.ip_allow(dp, 100, e1, ('10.0.2.0', '255.255.255.0'), ('10.0.3.0', '255.255.255.0'), e2)
        # ALLOW: h5,h6 -> h1,h2
        self.ip_allow(dp, 100, e2, ('10.0.3.0', '255.255.255.0'), ('10.0.1.0', '255.255.255.0'), e1)
        # ALLOW: h5,h6 reply -> h3,h4
        self.ip_allow(dp, 100, e2, ('10.0.3.0', '255.255.255.0'), ('10.0.2.0', '255.255.255.0'), e1)

        # BLOCK: h5,h6 -> h7,h8
        self.ip_drop(dp, 200, {'in_port': e2, 'ipv4_dst': ('10.0.4.0', '255.255.255.0')})
        # BLOCK: h7,h8 -> outside
        self.ip_drop(dp, 200, {'in_port': e3, 'ipv4_src': ('10.0.4.0', '255.255.255.0')})
        # BLOCK: outside -> h7,h8
        self.ip_drop(dp, 200, {'ipv4_dst': ('10.0.4.0', '255.255.255.0')})

    # =========================================================
    # s4: eth1=s2  eth2=h1  eth3=h2
    # =========================================================
    def install_s4(self, dp, p):
        e1 = p['s4-eth1']  # s2
        e2 = p['s4-eth2']  # h1
        e3 = p['s4-eth3']  # h2

        # ARP
        self.arp_flow(dp, 500, e1, [e2, e3])
        self.arp_flow(dp, 500, e2, [e1])
        self.arp_flow(dp, 500, e3, [e1])

        # ALLOW: h1 -> h5,h6
        self.ip_allow(dp, 100, e2, '10.0.1.1', ('10.0.3.0', '255.255.255.0'), e1)
        # ALLOW: h2 -> h5,h6
        self.ip_allow(dp, 100, e3, '10.0.1.2', ('10.0.3.0', '255.255.255.0'), e1)
        # ALLOW: h5,h6 -> h1
        self.ip_allow(dp, 100, e1, ('10.0.3.0', '255.255.255.0'), '10.0.1.1', e2)
        # ALLOW: h5,h6 -> h2
        self.ip_allow(dp, 100, e1, ('10.0.3.0', '255.255.255.0'), '10.0.1.2', e3)

        # BLOCK: -> h7,h8
        self.ip_drop(dp, 200, {'ipv4_dst': ('10.0.4.0', '255.255.255.0')})

    # =========================================================
    # s5: eth1=s2  eth2=h3  eth3=h4
    # =========================================================
    def install_s5(self, dp, p):
        e1 = p['s5-eth1']  # s2
        e2 = p['s5-eth2']  # h3
        e3 = p['s5-eth3']  # h4

        # ARP
        self.arp_flow(dp, 500, e1, [e2, e3])
        self.arp_flow(dp, 500, e2, [e1])
        self.arp_flow(dp, 500, e3, [e1])

        # ALLOW: h3 -> h5,h6
        self.ip_allow(dp, 100, e2, '10.0.2.1', ('10.0.3.0', '255.255.255.0'), e1)
        # ALLOW: h4 -> h5,h6
        self.ip_allow(dp, 100, e3, '10.0.2.2', ('10.0.3.0', '255.255.255.0'), e1)
        # ALLOW: h5,h6 reply -> h3
        self.ip_allow(dp, 100, e1, ('10.0.3.0', '255.255.255.0'), '10.0.2.1', e2)
        # ALLOW: h5,h6 reply -> h4
        self.ip_allow(dp, 100, e1, ('10.0.3.0', '255.255.255.0'), '10.0.2.2', e3)

        # BLOCK: -> h7,h8
        self.ip_drop(dp, 200, {'ipv4_dst': ('10.0.4.0', '255.255.255.0')})

    # =========================================================
    # s6: eth1=s3  eth2=h5  eth3=h6
    #
    # ICMP TRICK:
    #   icmp_type=0 (REPLY)   priority=300 ALLOW  <- h5 replying to h3
    #   icmp_type=8 (REQUEST) priority=200 DROP   <- h5 initiating to h3
    # =========================================================
    def install_s6(self, dp, p):
        e1 = p['s6-eth1']  # s3
        e2 = p['s6-eth2']  # h5
        e3 = p['s6-eth3']  # h6

        # ARP
        self.arp_flow(dp, 500, e1, [e2, e3])
        self.arp_flow(dp, 500, e2, [e1])
        self.arp_flow(dp, 500, e3, [e1])

        # ALLOW: h5 -> h1,h2
        self.ip_allow(dp, 100, e2, '10.0.3.1', ('10.0.1.0', '255.255.255.0'), e1)
        # ALLOW: h6 -> h1,h2
        self.ip_allow(dp, 100, e3, '10.0.3.2', ('10.0.1.0', '255.255.255.0'), e1)

        # ALLOW: h1,h2 -> h5
        self.ip_allow(dp, 100, e1, ('10.0.1.0', '255.255.255.0'), '10.0.3.1', e2)
        # ALLOW: h1,h2 -> h6
        self.ip_allow(dp, 100, e1, ('10.0.1.0', '255.255.255.0'), '10.0.3.2', e3)
        # ALLOW: h3,h4 -> h5
        self.ip_allow(dp, 100, e1, ('10.0.2.0', '255.255.255.0'), '10.0.3.1', e2)
        # ALLOW: h3,h4 -> h6
        self.ip_allow(dp, 100, e1, ('10.0.2.0', '255.255.255.0'), '10.0.3.2', e3)

        # ICMP TRICK: ALLOW echo REPLY (type=0) from h5 -> h3,h4 (priority 300)
        self.icmp_allow(dp, 300, e2, '10.0.3.1', ('10.0.2.0', '255.255.255.0'), 0, e1)
        # ICMP TRICK: ALLOW echo REPLY (type=0) from h6 -> h3,h4 (priority 300)
        self.icmp_allow(dp, 300, e3, '10.0.3.2', ('10.0.2.0', '255.255.255.0'), 0, e1)

        # BLOCK: h5 initiating -> h3,h4 (priority 200, loses to icmp reply at 300)
        self.ip_drop(dp, 200, {'in_port': e2, 'ipv4_src': '10.0.3.1', 'ipv4_dst': ('10.0.2.0', '255.255.255.0')})
        # BLOCK: h6 initiating -> h3,h4
        self.ip_drop(dp, 200, {'in_port': e3, 'ipv4_src': '10.0.3.2', 'ipv4_dst': ('10.0.2.0', '255.255.255.0')})

        # BLOCK: h5,h6 -> h7,h8
        self.ip_drop(dp, 200, {'in_port': e2, 'ipv4_dst': ('10.0.4.0', '255.255.255.0')})
        self.ip_drop(dp, 200, {'in_port': e3, 'ipv4_dst': ('10.0.4.0', '255.255.255.0')})

    # =========================================================
    # s7: eth1=s3  eth2=h7  eth3=h8  (ISOLATED)
    # =========================================================
    def install_s7(self, dp, p):
        e1 = p['s7-eth1']  # s3
        e2 = p['s7-eth2']  # h7
        e3 = p['s7-eth3']  # h8

        # ARP: only h7 <-> h8, block uplink
        self.arp_flow(dp, 500, e1, [])  # drop
        self.arp_flow(dp, 500, e2, [e3])
        self.arp_flow(dp, 500, e3, [e2])

        # ALLOW: h7 -> h8
        self.ip_allow(dp, 100, e2, '10.0.4.1', '10.0.4.2', e3)
        # ALLOW: h8 -> h7
        self.ip_allow(dp, 100, e3, '10.0.4.2', '10.0.4.1', e2)

        # BLOCK: uplink -> h7,h8
        self.ip_drop(dp, 200, {'in_port': e1})
        # BLOCK: h7 -> outside
        self.ip_drop(dp, 200, {'in_port': e2, 'ipv4_src': '10.0.4.1', 'ipv4_dst': ('10.0.1.0', '255.255.255.0')})
        self.ip_drop(dp, 200, {'in_port': e2, 'ipv4_src': '10.0.4.1', 'ipv4_dst': ('10.0.2.0', '255.255.255.0')})
        self.ip_drop(dp, 200, {'in_port': e2, 'ipv4_src': '10.0.4.1', 'ipv4_dst': ('10.0.3.0', '255.255.255.0')})
        # BLOCK: h8 -> outside
        self.ip_drop(dp, 200, {'in_port': e3, 'ipv4_src': '10.0.4.2', 'ipv4_dst': ('10.0.1.0', '255.255.255.0')})
        self.ip_drop(dp, 200, {'in_port': e3, 'ipv4_src': '10.0.4.2', 'ipv4_dst': ('10.0.2.0', '255.255.255.0')})
        self.ip_drop(dp, 200, {'in_port': e3, 'ipv4_src': '10.0.4.2', 'ipv4_dst': ('10.0.3.0', '255.255.255.0')})
