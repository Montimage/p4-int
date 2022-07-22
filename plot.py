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
    row[3] -= init

client_server_ips = ["10.0.0.11", "10.0.0.12", "10.0.1.11", "10.0.1.12"]
data = [row for row in data
    if  row[4] in ["int","tot"]          # interested reports
    and row[3] >= 0 and row[3] <= duration # testing duration
    and row[6] in client_server_ips      # interested clients and servers
    and row[7] in client_server_ips
    ]


ll_egress = [row for row in data if row[4] == "int" and row[6] == "10.0.0.11" and row[7] == "10.0.1.11" ]
cl_egress = [row for row in data if row[4] == "int" and row[6] == "10.0.0.12" and row[7] == "10.0.1.12" ]


ll_igress = [row for row in data if row[4] == "tot" and row[6] == "10.0.0.11" and row[7] == "10.0.1.11" ]
cl_igress = [row for row in data if row[4] == "tot" and row[6] == "10.0.0.12" and row[7] == "10.0.1.12" ]



def group_by_time( arr ):
    dic = {}
    for r in arr:
        for i in range(8, len(r)):
            r[i] = float(r[i])
        
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

ll_egress     = group_by_time(ll_egress)
cl_egress     = group_by_time(cl_egress)
ll_igress = group_by_time(ll_igress)
cl_igress = group_by_time(cl_igress)

print( len(ll_egress), len(cl_egress), len(ll_igress), len(cl_igress) )

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


def log_pkt( prefix, cl_egress, ll_egress ):
    print( prefix, "ll_egress = ", ll_egress, ", cl_egress = ", cl_egress, ", total = ", ll_egress+cl_egress)

log_pkt("ingress: ", cum(cl_igress, 9)[-1], cum(ll_igress, 9)[-1] )
log_pkt("egress:  ", cum(cl_egress, 10)[-1],    cum(ll_egress, 10)[-1] )



plt.rcParams['axes.xmargin'] = 0
plt.rcParams["figure.figsize"] = (8,6)
plt.tight_layout()


x_cl = get( cl_egress )
x_ll = get( ll_egress )

def draw(file_name, y_label, y_cl, y_ll, x_cl=x_cl, x_ll=x_ll, label_cl="CL traffic", label_ll="LL traffic", log_scale=False):
    #global x_cl, x_ll
    x_ll=range(0,len(y_ll))
    x_cl=range(0,len(y_cl))
    
    fig,ax1=plt.subplots()
    
    ax1.plot( x_cl, y_cl, linewidth=1,  color = 'b', label=label_cl )
    ax1.plot( x_ll, y_ll, linewidth=1,  color = 'r', label=label_ll )

    # giving labels to the axises
    #ax1.set_xlabel('time (s)')
    #ax1.set_ylabel( y_label )
    #we use xlabel  as title at the bottom
    ax1.set_xlabel( y_label, fontsize=16 )
    #ax2.set_ylabel('bandwidth (Mbps)')
    if log_scale:
        ax1.set_yscale('log')
     
    # defining display layout

    plt.xticks(range(0,duration+1,60))
    plt.grid()
    plt.legend(loc="upper right")

    # Save as pdf
    plt.savefig( output_dir + "/" + file_name, dpi=60, format='pdf', bbox_inches='tight')

draw( "bandwidth-egress.pdf",   "Egress bandwidth (Mbps)", 
    [row[9]*8/1000000.0 for row in cl_egress], [row[9]*8/1000000.0 for row in ll_egress] )
draw( "throughput-egress.pdf",  "Egress throughput (pps)", 
    get(cl_egress, 10), get(ll_egress, 10))

draw( "queue-delay.pdf", "Queue delay (ms/packet)", 
    [row[8]/1000.0/row[10] for row in cl_egress], [row[8]/1000.0/row[10] for row in ll_egress], log_scale=True )
draw( "queue-occup.pdf", "Queue occupancy (packets)",
    [row[13]/row[10] for row in cl_egress], [row[13]/row[10] for row in ll_egress] )

draw( "tcp-cwr.pdf", "TCP CWR signal (pps)",
    get(cl_egress, 16), get(ll_egress, 16) )


draw( "l4s-mark-cum.pdf",  "total marked packets", 
    cum( cl_egress, 11), cum(ll_egress, 11) )
draw( "l4s-mark.pdf",  "Marked packets (pps)", 
    get( cl_egress, 11), get(ll_egress, 11) )

draw( "l4s-drop.pdf",  "Total dropped packets", 
    cum( cl_egress, 12), cum(ll_egress, 12) )

draw( "l4s-mark-drop.pdf",  "L4S marked and dropped packets", 
    cum(ll_egress, 11), cum(ll_egress, 12),  label_cl="LL mark", label_ll="LL drop" )


draw( "bandwidth-ingress.pdf",   "Ingress bandwidth (Mbps)",     
    [int(row[8])*8/1000000.0 for row in cl_igress], [int(row[8])*8/1000000.0 for row in ll_igress] )
draw( "throughput-ingress.pdf", "Ingress throughput (pps)", 
    get(cl_igress, 9), get(ll_igress, 9))

# difference between igress and egress
# not in the same timestamp
#draw( "drop-ingress-egress-throughput.pdf", "dropped throughput (pps)", 
#    diff(cl_igress, cl_egress, 9, 10), diff(ll_igress, ll_egress, 9, 10))
#draw( "drop-ingress-egress-total.pdf", "total dropped (pps)", 
#    cum(diff(cl_igress, cl_egress, 9, 10)), cum(diff(ll_igress, ll_egress, 9, 10)))
