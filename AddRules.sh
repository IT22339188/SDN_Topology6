#!/bin/bash
# ============================================================
# IE4080 - Assignment 2 - Topology 6
# Part A: Direct OpenFlow Rule Installation
# ============================================================

echo "========================================"
echo " IE4080 Topology 6 - Installing Rules"
echo " Part A: Direct OpenFlow Rules"
echo "========================================"

# STEP 1: Clear all existing flows
echo ""
echo "[1/9] Clearing all existing flows..."
for sw in s1 s2 s3 s4 s5 s6 s7; do
    ovs-ofctl -O OpenFlow13 del-flows $sw
    echo "      Cleared: $sw"
done

# STEP 2: ARP RULES
echo ""
echo "[2/9] Installing ARP rules..."

ovs-ofctl -O OpenFlow13 add-flow s1 "priority=500,arp,in_port=1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=500,arp,in_port=2,actions=output:1"

ovs-ofctl -O OpenFlow13 add-flow s2 "priority=500,arp,in_port=1,actions=output:2,output:3"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=500,arp,in_port=2,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=500,arp,in_port=3,actions=output:1"

ovs-ofctl -O OpenFlow13 add-flow s3 "priority=500,arp,in_port=1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=500,arp,in_port=2,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=500,arp,in_port=3,actions=drop"

ovs-ofctl -O OpenFlow13 add-flow s4 "priority=500,arp,in_port=1,actions=output:2,output:3"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=500,arp,in_port=2,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=500,arp,in_port=3,actions=output:1"

ovs-ofctl -O OpenFlow13 add-flow s5 "priority=500,arp,in_port=1,actions=output:2,output:3"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=500,arp,in_port=2,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=500,arp,in_port=3,actions=output:1"

ovs-ofctl -O OpenFlow13 add-flow s6 "priority=500,arp,in_port=1,actions=output:2,output:3"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=500,arp,in_port=2,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=500,arp,in_port=3,actions=output:1"

ovs-ofctl -O OpenFlow13 add-flow s7 "priority=500,arp,in_port=1,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=500,arp,in_port=2,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=500,arp,in_port=3,actions=output:2"

echo "      ARP rules installed."

# STEP 3: S1 - Core
echo ""
echo "[3/9] Installing rules on s1 (Core)..."

ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100,ip,in_port=1,nw_src=10.0.1.0/24,nw_dst=10.0.3.0/24,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100,ip,in_port=1,nw_src=10.0.2.0/24,nw_dst=10.0.3.0/24,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100,ip,in_port=2,nw_src=10.0.3.0/24,nw_dst=10.0.1.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=100,ip,in_port=2,nw_src=10.0.3.0/24,nw_dst=10.0.2.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=200,ip,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=200,ip,nw_src=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s1 "priority=1,actions=drop"

echo "      s1 rules installed."

# STEP 4: S2 - Distribution Left
echo ""
echo "[4/9] Installing rules on s2 (Distribution - left)..."

ovs-ofctl -O OpenFlow13 add-flow s2 "priority=100,ip,in_port=2,nw_src=10.0.1.0/24,nw_dst=10.0.3.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=100,ip,in_port=3,nw_src=10.0.2.0/24,nw_dst=10.0.3.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=100,ip,in_port=1,nw_src=10.0.3.0/24,nw_dst=10.0.1.0/24,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=100,ip,in_port=1,nw_src=10.0.3.0/24,nw_dst=10.0.2.0/24,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=200,ip,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s2 "priority=1,actions=drop"

echo "      s2 rules installed."

# STEP 5: S3 - Distribution Right
echo ""
echo "[5/9] Installing rules on s3 (Distribution - right)..."

ovs-ofctl -O OpenFlow13 add-flow s3 "priority=100,ip,in_port=1,nw_src=10.0.1.0/24,nw_dst=10.0.3.0/24,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=100,ip,in_port=1,nw_src=10.0.2.0/24,nw_dst=10.0.3.0/24,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=100,ip,in_port=2,nw_src=10.0.3.0/24,nw_dst=10.0.1.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=100,ip,in_port=2,nw_src=10.0.3.0/24,nw_dst=10.0.2.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=200,ip,in_port=2,nw_src=10.0.3.0/24,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=200,ip,in_port=3,nw_src=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=200,ip,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s3 "priority=1,actions=drop"

echo "      s3 rules installed."

# STEP 6: S4 - Access H1,H2
echo ""
echo "[6/9] Installing rules on s4 (Access - h1,h2)..."

ovs-ofctl -O OpenFlow13 add-flow s4 "priority=100,ip,in_port=2,nw_src=10.0.1.1,nw_dst=10.0.3.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=100,ip,in_port=3,nw_src=10.0.1.2,nw_dst=10.0.3.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=100,ip,in_port=1,nw_src=10.0.3.0/24,nw_dst=10.0.1.1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=100,ip,in_port=1,nw_src=10.0.3.0/24,nw_dst=10.0.1.2,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=200,ip,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s4 "priority=1,actions=drop"

echo "      s4 rules installed."

# STEP 7: S5 - Access H3,H4
echo ""
echo "[7/9] Installing rules on s5 (Access - h3,h4)..."

ovs-ofctl -O OpenFlow13 add-flow s5 "priority=100,ip,in_port=2,nw_src=10.0.2.1,nw_dst=10.0.3.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=100,ip,in_port=3,nw_src=10.0.2.2,nw_dst=10.0.3.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=100,ip,in_port=1,nw_src=10.0.3.0/24,nw_dst=10.0.2.1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=100,ip,in_port=1,nw_src=10.0.3.0/24,nw_dst=10.0.2.2,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=200,ip,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s5 "priority=1,actions=drop"

echo "      s5 rules installed."

# STEP 8: S6 - Access H5,H6 (ICMP trick)
echo ""
echo "[8/9] Installing rules on s6 (Access - h5,h6) with ICMP trick..."

ovs-ofctl -O OpenFlow13 add-flow s6 "priority=100,ip,in_port=2,nw_src=10.0.3.1,nw_dst=10.0.1.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=100,ip,in_port=3,nw_src=10.0.3.2,nw_dst=10.0.1.0/24,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=100,ip,in_port=1,nw_src=10.0.1.0/24,nw_dst=10.0.3.1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=100,ip,in_port=1,nw_src=10.0.1.0/24,nw_dst=10.0.3.2,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=100,ip,in_port=1,nw_src=10.0.2.0/24,nw_dst=10.0.3.1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=100,ip,in_port=1,nw_src=10.0.2.0/24,nw_dst=10.0.3.2,actions=output:3"

# ICMP TRICK: Allow echo REPLY (type=0) priority 300
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=300,icmp,in_port=2,nw_src=10.0.3.1,nw_dst=10.0.2.0/24,icmp_type=0,actions=output:1"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=300,icmp,in_port=3,nw_src=10.0.3.2,nw_dst=10.0.2.0/24,icmp_type=0,actions=output:1"

# BLOCK: h5,h6 initiating to h3,h4 priority 200
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=200,ip,in_port=2,nw_src=10.0.3.1,nw_dst=10.0.2.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=200,ip,in_port=3,nw_src=10.0.3.2,nw_dst=10.0.2.0/24,actions=drop"

ovs-ofctl -O OpenFlow13 add-flow s6 "priority=200,ip,in_port=2,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=200,ip,in_port=3,nw_dst=10.0.4.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s6 "priority=1,actions=drop"

echo "      s6 rules installed."

# STEP 9: S7 - Access H7,H8 ISOLATED
echo ""
echo "[9/9] Installing rules on s7 (Access - h7,h8 ISOLATED)..."

ovs-ofctl -O OpenFlow13 add-flow s7 "priority=100,ip,in_port=2,nw_src=10.0.4.1,nw_dst=10.0.4.2,actions=output:3"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=100,ip,in_port=3,nw_src=10.0.4.2,nw_dst=10.0.4.1,actions=output:2"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=1,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=2,nw_src=10.0.4.1,nw_dst=10.0.1.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=2,nw_src=10.0.4.1,nw_dst=10.0.2.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=2,nw_src=10.0.4.1,nw_dst=10.0.3.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=3,nw_src=10.0.4.2,nw_dst=10.0.1.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=3,nw_src=10.0.4.2,nw_dst=10.0.2.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=200,ip,in_port=3,nw_src=10.0.4.2,nw_dst=10.0.3.0/24,actions=drop"
ovs-ofctl -O OpenFlow13 add-flow s7 "priority=1,actions=drop"

echo "      s7 rules installed."

echo ""
echo "========================================"
echo " All rules installed successfully!"
echo "========================================"
echo ""
echo " Expected pingall result:"
echo "   h1 -> X X X h5 h6 X X"
echo "   h2 -> X X X h5 h6 X X"
echo "   h3 -> X X X h5 h6 X X"
echo "   h4 -> X X X h5 h6 X X"
echo "   h5 -> h1 h2 X X X X X"
echo "   h6 -> h1 h2 X X X X X"
echo "   h7 -> X X X X X X h8"
echo "   h8 -> X X X X X X h7"
echo "========================================"
