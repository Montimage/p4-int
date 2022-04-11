#!/bin/bash -x

if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  exit
fi

#compile code
#p4c  --target  bmv2  --arch  v1model  L4S_v3.p4

if [ $? != 0 ]
then
  echo "Could not compile P4" >&2
  exit 1
fi

rm -rf log/*

# create new virtual NIC to test P4
#https://opennetworking.org/news-and-events/blog/getting-started-with-p4/
function config-nic(){

	NIC=$1
   MAC=$2

	ip link set dev $NIC up
   ip link set dev $NIC address $MAC
	ip link set $NIC mtu 1500
   ethtool -K $NIC tso off gso off gro off tx off
	sysctl net.ipv6.conf.$NIC.disable_ipv6=1
}

function create-virtual-nic(){
   NIC_1=$1
   MAC_1=$2
   NIC_2=$3
   MAC_2=$4

	ip link add name $NIC_1 type veth peer name $NIC_2
   config-nic $NIC_1 $MAC_1
   config-nic $NIC_2 $MAC_2
}

#to delete virtual NIC:
#ip link delete veth_a

create-virtual-nic "veth_a" "00:00:00:00:00:a0" "veth_a1" "00:00:00:00:00:a1"
create-virtual-nic "veth_b" "00:00:00:00:00:a0" "veth_b1" "00:00:00:00:00:b1"
create-virtual-nic "veth_c" "00:00:00:00:00:c0" "veth_c1" "00:00:00:00:00:c1"
create-virtual-nic "veth_d" "00:00:00:00:00:d0" "veth_d1" "00:00:00:00:00:d1"

ifconfig veth_a 10.0.0.1

#create "server" namespace
ip netns add server
function run_on_ns(){
   ip netns exec server "$@"
}
#add veth_a1 to "server" namespace
ip link set veth_d1 netns server
sysctl -w net.ipv4.ip_forward=1
run_on_ns ifconfig veth_d1 10.0.0.3
run_on_ns sysctl net.ipv6.conf.veth_d1.disable_ipv6=1
run_on_ns sysctl -w net.ipv4.ip_forward=1
run_on_ns ifconfig veth_d1 up
run_on_ns ethtool -K veth_d1 tso off gso off gro off tx off

#running a proc that use "server" namespace


SW_A_B_PORT=9091
SW_B_C_PORT=9092
SW_C_D_PORT=9093

function create_switch(){
   NIC_1=$1
   NIC_2=$2
   THRIFT_PORT=$3
   ID=$4
   FILE=$5
   echo "Creating a bridge using simple_switch: $@"
   #/home/montimage/github/behavioral-model/targets/simple_switch/simple_switch   --pcap  --log-console --log-level debug  -i 1@veth_a -i 2@veth_b --thrift-port 9090 $FILE &
   DEBUG="--log-file log/sw-$ID.log  --log-level debug --pcap log/" 
   #disable debug
   #DEBUG=""
   simple_switch $DEBUG --device-id $ID -i 1@$NIC_1 -i 2@$NIC_2 --queue 2 --thrift-port $THRIFT_PORT --ll_queue 64 --BE_queue 128 $FILE
   echo "simple_switch $ID returned code: $?"
   #/usr/local/bin/simple_switch "$@"
}

#veth_a--veth_a1 ==X== veth_b--veth_b1 ==X== veth_c--veth_c1
#create_switch "veth_a1" "veth_b" "$SW_A_B_PORT" "1" switch-l4s.json &
create_switch "veth_a1" "veth_b" "$SW_A_B_PORT" "1" switch-l4s.json &
create_switch "veth_b1" "veth_c" "$SW_B_C_PORT" "2" switch-int.json 2>&1 > log/sw-2-simple.log &
create_switch "veth_c1" "veth_d" "$SW_C_D_PORT" "3" switch-int.json 2>&1 > log/sw-3-simple.log &


#wait for simple_switch
sleep 2

function config_sw_ab(){
   /usr/local/bin/simple_switch_CLI --thrift-port "$SW_A_B_PORT" "$@"
}

function config_sw_bc(){
   /usr/local/bin/simple_switch_CLI --thrift-port "$SW_B_C_PORT" "$@"
}

function config_sw_cd(){
   /usr/local/bin/simple_switch_CLI --thrift-port "$SW_C_D_PORT" "$@"
}
#table_add ipv4_lpm ipv4_forward 192.168.109.214 => 00:00:00:00:00:a0 00:00:00:00:00:a1 1

#IP forwarding
# Syntax:
# ip_dst => mac_src mac_dst egress_port


# config le switch A-B

cat <<EOF | config_sw_ab
table_set_default ipv4_lpm drop
table_add select_mcast_grp set_mcast_grp 1 => 1
table_add select_mcast_grp set_mcast_grp 2 => 2
table_add ipv4_lpm ipv4_forward 10.0.0.1 => 00:00:00:00:00:a1 00:00:00:00:00:a0 1
table_add ipv4_lpm ipv4_forward 10.0.0.3 => 00:00:00:00:00:b0 00:00:00:00:00:b1 2
table_add select_PI2_param set_PI2_param => 1342 13421 15000 14
table_add select_L4S_param set_L4S_param => 5000 3000 0 1500 21
table_add select_Classic_Protection set_Classic_Protection => 1
EOF

#cat <<EOF | config_sw_ab
#table_add ipv4_lpm ipv4_forward 10.0.0.1 => 00:00:00:00:00:a1 00:00:00:00:00:a0 1
#table_add ipv4_lpm ipv4_forward 10.0.0.3 => 00:00:00:00:00:b0 00:00:00:00:00:b1 2
#EOF


cat <<EOF | config_sw_bc
table_add ipv4_lpm ipv4_forward 10.0.0.1 => 00:00:00:00:00:b1 00:00:00:00:00:b0 1
table_add ipv4_lpm ipv4_forward 10.0.0.3 => 00:00:00:00:00:c0 00:00:00:00:00:c1 2
EOF


# the last switch simple forwards packets
cat <<EOF | config_sw_cd
table_add ipv4_lpm ipv4_forward 10.0.0.1 => 00:00:00:00:00:c1 00:00:00:00:00:c0 1
table_add ipv4_lpm ipv4_forward 10.0.0.3 => 00:00:00:00:00:d0 00:00:00:00:00:d1 2
EOF



# CONFIGURE In-band network telemetry
# enable INT
# => set switch ID
cat <<EOF | config_sw_ab
table_add tb_int_config_transit set_transit => 1
EOF

cat <<EOF | config_sw_bc
table_add tb_int_config_transit set_transit => 2
EOF

cat <<EOF | config_sw_cd
table_add tb_int_config_transit set_transit => 3
EOF


# set source
# ip_src ip_dst port_src port_dst => max_hop hop_md_length inst_mask priority
cat <<EOF | config_sw_ab
table_add tb_int_config_source set_source 10.0.0.1&&&0xFFFFFF00 5001&&&0x0000 10.0.0.3&&&0xFFFFFFFF 5001&&&0xFFFF => 4 10 0xFFFF 0
table_add tb_int_config_source set_source 10.0.0.1&&&0xFFFFFF00 5001&&&0x0000 10.0.0.3&&&0xFFFFFFFF 5002&&&0xFFFF => 4 10 0xFFFF 0
EOF


# set sink node
# egress_port => sink_reporting_port
#
# sink_reporting_port is not supported for now

#cat <<EOF | config_sw_ab
#table_add tb_int_config_sink set_sink 1 => 0
#EOF

cat <<EOF | config_sw_cd
table_add tb_int_config_sink set_sink 2 => 0
EOF


# ping does not reply when having this
#  set_egress_mahimahi 2 33

#fixed in arp cache
arp -s           10.0.0.3 00:00:00:00:00:a0
run_on_ns arp -s 10.0.0.1 00:00:00:00:00:d1


echo "====HN test ping"
ping 10.0.0.3 -c 1

#run_on_ns iperf3 --port 5001 --server  &

function run_iperf_udp(){
   echo "====HN test iperf"
   # handle one client connection then exit
   run_on_ns iperf3 --server --one-off --port 5001 &
   sleep 1
   # send only 1k/second
   iperf3 --client 10.0.0.3 --port 5001 --udp --bandwidth 1K --set-mss 1000 --length 1000  --interval 1 --time 3600
   IPERF_PID=$!
   sleep 2
   killall iperf3
   sleep 1
   killall -9 iperf3 2> /dev/null
}

#run_iperf_udp


function run_iperf_tcp(){
   echo "====HN test iperf"
   # handle one client connection then exit
   run_on_ns iperf3 --server --one-off --port 5001 &
   sleep 1
   # send only 1k/second
   iperf3 --client 10.0.0.3 --port 5001 --bandwidth 10M --set-mss 946 --length 946  --interval 1 --bytes 946
   #IPERF_PID=$!
   #sleep 2
   #killall iperf3
   #sleep 1
   #killall -9 iperf3 2> /dev/null
}

#run_iperf_tcp


function run_udp(){
   echo "====HN test UDP using netcat"
   PARAM="-u -4" #udp, ipv4
   #PARAM="-4" #ipv4
   run_on_ns nc $PARAM -lkp 5001 &
   sleep 1
   set +x
   #while [[ true ]]; do echo "mosaico `date`" && sleep 1; done | nc $PARAM 10.0.0.3 5001
   echo "mosaico `date`" | nc $PARAM 10.0.0.3 5001 &
   sleep 1
   killall -9 nc
}

run_udp

echo
echo "in bash ..."
#run a bash terminal without EVN
run_on_ns iperf3 --server --port 5001 &
run_on_ns iperf3 --server --port 5002 &
env --ignore-environment PS1="demo: " bash --norc --noprofile

#simple_switch_CLI

# put simple_siwtch to forground
killall iperf3
killall -9 iperf3 2> /dev/null

killall -2 simple_switch

sleep 1
