import os
import matplotlib as mpl
if os.environ.get('DISPLAY','') == '':
    print('no display found. Using non-interactive Agg backend')
    mpl.use('Agg')

from matplotlib import pyplot as plt

import numpy as np
import csv, sys
import matplotlib


file_name = sys.argv[1]

output_dir = file_name + ".out"

if not os.path.exists( output_dir ):
    os.mkdir( output_dir )

reader = csv.reader( open( file_name ))
data = [row for row in reader if row[0] == "999"]

unit=1000
unit=1 #1second
time_from =  5*unit
duration  = 300*unit
init=0

# update timestamp
for row in data:
    row[3] = int(float(row[3]) * unit)
    if init==0 :
        init = row[3]+time_from

    #specific for UDP
    # change its IP source to be classified as unresponsive ECN traffic
    l = len(row)-1
    if row[l].startswith("99."):
        if row[ l ] == "99.178.376.658" or row[ l ] == "99.178.376.0":
            row[6] = "10.0.0.12"
        row[l] = 0 #avoid error when convertint to float

    for i in range(8, len(row)):
        row[i] = float(row[i])
        # ECN
        if i == 17 and row[i] > 1:
            row[i] -= 2
    row[3] -= init

client_server_ips = ["10.0.0.11", "10.0.0.12", "10.0.1.11", "10.0.1.12"]
data = [row for row in data
    if  row[4] in ["int","tot"]          # interested reports
    and row[3] >= 0 and row[3] <= duration # testing duration
    and row[6] in client_server_ips      # interested clients and servers
    and row[7] in client_server_ips
    ]



l1_egress = [row for row in data if row[4] == "int" and row[7] == "10.0.1.11" and  row[6] == "10.0.0.11" ]
l2_egress = [row for row in data if row[4] == "int" and row[7] == "10.0.1.11" and  row[6] == "10.0.0.12" ]
ll_egress = [row for row in data if row[4] == "int" and row[7] == "10.0.1.11" and (row[6] == "10.0.0.11" or row[6] == "10.0.0.12") ]
cl_egress = [row for row in data if row[4] == "int" and row[7] == "10.0.1.12" and  row[6] == "10.0.0.12" ]

l1_igress = [row for row in data if row[4] == "tot" and row[7] == "10.0.1.11" and  row[6] == "10.0.0.11" ]
l2_igress = [row for row in data if row[4] == "tot" and row[7] == "10.0.1.11" and  row[6] == "10.0.0.12" ]
ll_igress = [row for row in data if row[4] == "tot" and row[7] == "10.0.1.11" and (row[6] == "10.0.0.11" or row[6] == "10.0.0.12") ]
cl_igress = [row for row in data if row[4] == "tot" and row[7] == "10.0.1.12" and  row[6] == "10.0.0.12" ]

def copy( arr ):
    result=[]
    for i in range(0, len(arr)):
        result.append( arr[i] )
    return result

def group_by_time( arr ):
    dic = {}
    for r in arr:
        r = copy(r)

        
        time=r[3]
        if time in dic:
            old = dic[time]

            for i in range(8, len(r)):
                old[i] += r[i]
        else:
            dic[time] = r
    arr = []
    for time in dic:
        arr.append(dic[time])
    arr = sorted(arr, key=lambda x: int(x[3]))
    #print( arr[0:10] )
    return arr

l1_egress = group_by_time(l1_egress)
l2_egress = group_by_time(l2_egress)
ll_egress = group_by_time(ll_egress)
cl_egress = group_by_time(cl_egress)

l1_igress = group_by_time(l1_igress)
l2_igress = group_by_time(l2_igress)
ll_igress = group_by_time(ll_igress)
cl_igress = group_by_time(cl_igress)


#specific for using UDP ar abnormal
#l2_igress = l2_egress
#cl_egress = cl_igress

print( len(ll_egress), len(cl_egress), len(ll_igress), len(cl_igress) )
print( len(l1_egress), len(l2_egress), len(l1_igress), len(l2_igress) )


#length = min( len(ll_egress), len(cl_egress), len(ll_igress), len(cl_igress) )
#ll_egress=ll_egress[0:length]
#cl_egress=cl_egress[0:length]
#ll_igress=ll_igress[0:length]
#cl_igress=cl_igress[0:length]
# test only LL traffic
#cl_egress=ll_egress
#cl_igress=ll_igress

def get(a, index=3):
    return [row[ index ] for row in a]

def cum( a, index=-1 ):
    tot = 0
    result = []
    print(a[0])
    if index >= 0:
        for i in range(0, len(a) ):
            tot += a[i][index]
            result.append( tot )

    else:
        for i in range(0, len(a) ):
            tot += a[i]
            result.append( tot )
    #print(result)
    return result

def diff( a1, a2, i1, i2 ):
    result = []
    for i in range(0, len(a1)):
        v1 = a1[i]
        v2 = a2[i]
        # must be the same timestamp
        if v1[3] != v2[3]:
            print("Error ", v1, v2)
            return
        result.append( v1[i1] - v2[i2] )
    print(result)
    return result


def log_pkt( prefix, cl, ll, l1, l2 ):
    print( prefix, "cl = ", cl, ", ll = ", ll, "( l1 = ", l1, ", l2 = ", l2, "), total = ", ll+cl)

log_pkt("ingress: ", cum(cl_igress, 9) [-1], cum(ll_igress, 9) [-1], cum(l1_igress, 9) [-1], cum(l2_igress, 9) [-1] )
#log_pkt("egress:  ", cum(cl_egress, 10)[-1], cum(ll_egress, 10)[-1], cum(l1_egress, 10)[-1], cum(l2_egress, 10)[-1] )


plt.rcParams['axes.xmargin'] = 0
plt.rcParams["figure.figsize"] = (8,6)
plt.tight_layout()


x_cl = get( cl_egress )
x_ll = get( ll_egress )

def draw(file_name, y_label, y_axes, labels=["Classic traffic", "LL traffic", "Legitimate LL traffic", "Unresponsive LL traffic"], log_scale=False ):
    #global x_cl, x_ll
    fig,ax1=plt.subplots()
    colors=['blue', 'red', 'magenta', 'peru']
    
    for i in range(0, len(y_axes)):
        if i==1: #ignore LL
            continue
        y = y_axes[i]
        ax1.plot( range(0,len(y)), y, linewidth=1,  color=colors[i], label=labels[i] )

    # giving labels to the axises
    #ax1.set_xlabel('time (s)')
    #ax1.set_ylabel( y_label )
    #ax2.set_ylabel('bandwidth (Mbps)')
    #we use xlabel  as title at the bottom
    ax1.set_xlabel( y_label, fontsize=16 )
    if log_scale:
        ax1.set_yscale('log')

    # defining display layout

    plt.xticks(range(0,duration+1,60))
    plt.grid()
    plt.legend(loc="upper right")

    # Save as pdf
    plt.savefig( output_dir + "/" + file_name, dpi=60, format='pdf', bbox_inches='tight')

def bw( arr, index=9 ):
    result=[]
    for i in range(0, len(arr)):
        result.append( arr[i][index] * 8.0/1000000 )
    return result

draw( "bandwidth-egress.pdf",   "Egress bandwidth (Mbps)", 
    [ bw(cl_egress), bw(ll_egress), bw(l1_egress), bw(l2_egress)])
draw( "bandwidth-ingress.pdf",   "Ingress bandwidth (Mbps)", 
    [ bw(cl_igress,8), bw(ll_igress,8), bw(l1_igress,8), bw(l2_igress,8)] )

draw( "throughput-egress.pdf",  "Egress throughput (pps)", 
    [get(cl_egress,10), get(ll_egress,10), get(l1_egress,10), get(l2_egress,10)] )
draw( "throughput-ingress.pdf",  "Ingress throughput (pps)", 
    [get(cl_igress,9), get(ll_igress,9), get(l1_igress,9), get(l2_igress,9)] )


def delay( arr ):
    result=[]
    for i in range(0, len(arr)):
        r = arr[i]
        result.append( r[8]/ 1000 / r[10] )
    return result

draw( "queue-delay.pdf", "Queue delay (ms/packet)", 
    [ delay(cl_egress), delay(ll_egress), delay(l1_egress), delay(l2_egress)], log_scale=True )

def occup( arr ):
    result=[]
    for i in range(0, len(arr)):
        r = arr[i]
        result.append( r[13] / r[10] )
    return result

draw( "queue-occup.pdf", "Queue occupancy (packets)",
    [ occup(cl_egress), occup(ll_egress), occup(l1_egress), occup(l2_egress)] )

draw( "l4s-mark-cum.pdf",  "Total marked packets", 
    [cum( cl_egress, 11), cum(ll_egress, 11), cum(l1_egress, 11), cum(l2_egress, 11)] )

draw( "l4s-mark.pdf",  "# marked packets/second", 
    [get( cl_egress, 11), get(ll_egress, 11), get(l1_egress, 11), get(l2_egress, 11)] )


draw( "tcp-ece.pdf",  "Total number of TCP ECN-Echo signals", 
    [get(cl_egress,15), get(ll_egress,15), get(l1_egress,15), get(l2_egress,15)] )
draw( "tcp-cwr.pdf",  "TCP CWR signal (pps)", 
    [get(cl_egress,16), get(ll_egress,16), get(l1_egress,16), get(l2_egress,16)] )

draw( "ecn-mark.pdf",  "Total marked packets", 
    [cum( cl_egress, 17), cum(ll_egress, 17), cum(l1_egress, 17), cum(l2_egress, 17)] )

draw( "l4s-drop.pdf",  "Total dropped packets", 
    [cum( cl_egress, 12), cum(ll_egress, 12), cum(l1_egress, 12), cum(l2_egress, 12)] )

draw( "l4s-mark-drop.pdf",  "L4S marked and dropped packets", 
    [cum(ll_egress, 11), cum(ll_egress, 12)],  ["LL mark", "LL drop"] )
#
#


# difference between igress and egress
# not in the same timestamp
#draw( "drop-ingress-egress-throughput.pdf", "dropped throughput (pps)", 
#    diff(cl_igress, cl_egress, 9, 10), diff(ll_igress, ll_egress, 9, 10))
#draw( "drop-ingress-egress-total.pdf", "total dropped (pps)", 
#    cum(diff(cl_igress, cl_egress, 9, 10)), cum(diff(ll_igress, ll_egress, 9, 10)))
