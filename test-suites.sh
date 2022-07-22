source ./environment.sh

DELAY=100ms

function hn-start-mmt(){
	# start mmt to monitor
	rm 16*.csv

	(
	# defautl: INT
	mmt-probe -c ./mmt-probe-int.conf 2>&1  &
	# iface on clients to get total traffic
	mmt-probe -c ./mmt-probe-tot.conf 2>&1  &
	) > log/mmt-probes.log &
	tcpdump -i enp0s10 -w /tmp/enp0s10.pcap &
}

function hn-stop-mmt(){
	killall -2 mmt-probe
	killall -2 tcpdump
	sleep 1
	tar -czf log/enp0s10.pcap.tar.gz /tmp/enp0s10.pcap
	cat 16*data*.csv > log/data.csv
	rm 16*data*.csv
}

function hn-stop-all-test(){
	run-on-all-endhost screen -XS hn quit
	sleep 2
	run-on-all-endhost screen -XS hn2 quit
}


function hn-run-test-using-iperf(){
	if [[ "$#" -lt "3" ]]; then
		echo "Need 3 parameters: bandwidth-a bandwidth-b test-duration"
		return
	fi

	hn-start-mmt &
	sleep 2
	
	
	BANDWIDTH_A=$1
	BANDWIDTH_B=$2
	TIME=$3
	
	run-on-host $CLIENT_A screen -S hn -dm iperf3 -c $SERVER_A --set-mss 1400 --length 1400 --time 600 --bandwidth $BANDWIDTH_A
	run-on-host $CLIENT_B screen -S hn -dm iperf3 -c $SERVER_B --set-mss 1400 --length 1400 --time 600 --bandwidth $BANDWIDTH_B
	run-on-host $CLIENT_B screen -S hn -dm iperf3 -c $SERVER_B --set-mss 1400 --length 1400 --time 600 --bandwidth $BANDWIDTH_B --port 22223
	
	
	sleep $TIME
	sleep 5
	hn-stop-mmt
	hn-stop-all-test
	killall -2 simple_switch

	sleep 2

	mv log "log-${BANDWIDTH_A}bps-${BANDWIDTH_B}bps-${TIME}s-delay$DELAY-$4-$(now)"
	exit 0
}

function hn-setup-traffic-iperf-on-server(){
	hn-stop-all-test
	#clean up tc rule
	run-on-host $CLIENT_A sudo tc qdisc del dev $CLIENT_A_IFACE root
	run-on-host $CLIENT_B sudo tc qdisc del dev $CLIENT_B_IFACE root
	run-on-host $SERVER_A sudo tc qdisc del dev $SERVER_A_IFACE root
	run-on-host $SERVER_B sudo tc qdisc del dev $SERVER_B_IFACE root
	
	run-on-host $CLIENT_A sudo tc qdisc change dev $CLIENT_A_IFACE root netem delay  $DELAY
	run-on-host $CLIENT_B sudo tc qdisc change dev $CLIENT_B_IFACE root netem delay  $DELAY
	run-on-host $SERVER_A sudo tc qdisc change dev $SERVER_A_IFACE root netem delay  $DELAY
	run-on-host $SERVER_B sudo tc qdisc change dev $SERVER_B_IFACE root netem delay  $DELAY
	
	run-on-host $CLIENT_A sudo sysctl -w net.ipv4.tcp_congestion_control=dctcp
	run-on-host $SERVER_A sudo sysctl -w net.ipv4.tcp_congestion_control=dctcp
	
	run-on-host $CLIENT_B sudo sysctl -w net.ipv4.tcp_congestion_control=cubic
	run-on-host $SERVER_B sudo sysctl -w net.ipv4.tcp_congestion_control=cubic
	
	# Enable/disable ECN on corresponding clients/servers
	run-on-host $CLIENT_A sudo sysctl -w net.ipv4.tcp_ecn=1
	run-on-host $SERVER_A sudo sysctl -w net.ipv4.tcp_ecn=1

	run-on-host $CLIENT_B sudo sysctl -w net.ipv4.tcp_ecn=0
	run-on-host $SERVER_B sudo sysctl -w net.ipv4.tcp_ecn=0


	#start iperf server
	run-on-host $SERVER_A screen -S hn -dm iperf3 -s
	run-on-host $SERVER_B screen -S hn -dm iperf3 -s
	run-on-host $SERVER_B screen -S hn2 -dm iperf3 -s --port 22223
}

BW=5M
function hn-run-abnormal-traffic-iperf-on-server(){
	
	hn-setup-traffic-iperf-on-server
	
	#start another iperf server
	run-on-host $SERVER_A screen -S hn2 -dm iperf3 -s --port 22222
	sleep 1
	run-on-host $CLIENT_A screen -S hn2 -dm iperf3 -c $SERVER_A --bandwidth 10M  --set-mss 1400 --length 1400 --time 600 --port 22222 --udp
	
	hn-run-test-using-iperf $BW $BW 310 abnormal-dctp-udp-10Mb-cubic-cubic-delay-$DELAY
}


function hn-run-normal-traffic-iperf-on-server(){
	
	hn-setup-traffic-iperf-on-server
	
	#start another iperf server
	run-on-host $SERVER_A screen -S hn2 -dm iperf3 -s --port 22222
	sleep 1
	run-on-host $CLIENT_A screen -S hn2 -dm iperf3 -c $SERVER_A --bandwidth $BW  --set-mss 1400 --length 1400 --time 600 --port 22222
	
	hn-run-test-using-iperf $BW $BW 310 normal-dctp-cubic-cubic-delay-$DELAY
}


HISTORY_LOG="bash-history.log"
date >> $HISTORY_LOG
export HISTFILE=$HISTORY_LOG
export PS1='$(date) bash demo: '
set -x