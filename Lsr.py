'''
COMP9331 Computer Networks and Applications
Asssignment for T2 2019 (19T2)
Due: 17:00 Friday 9th August 2019
Lsr.py
By Fan Zhu z5245075@ad.unsw.edu.au

This is a program that implements the link state routing protocol.
The program mimics a router and how a router in a network would
act, the program handles both transmission and recieving like a
network router would and stores and builds the overall network
topoplogy.

Further details are included in the report:
report.pdf
'''
from socket import *
import sys
import time
import copy

#global variables
UPDATE_INTERVAL = 1
HEARTBEAT_INTERVAL = 0.2
ROUTE_UPDATE_INTERVAL = 30

#function to read input .txt file
def read_txt(fp):
    line_list = []
    routers = []
    neighbour_ports = {}
    with open(fp) as file:
        for line in file:
            line_list.append(line.split())

        my_router = [line_list[0][0], int(line_list[0][1])]

        i = 2
        while i < len(line_list):
            routers.append([line_list[i][0], float(line_list[i][1])])
            neighbour_ports.update({line_list[i][0]: int(line_list[i][2])})
            i+=1
            
        return routers, neighbour_ports, my_router
    
#simple UDP sender function
def sender(s_port, message):
    clientSocket = socket(AF_INET, SOCK_DGRAM)
    s_msg = message.encode(encoding = 'utf-8')
    clientSocket.sendto(s_msg,('localhost', s_port))
    
#function to sort dictionary (somewhat unecessary)
def sort_dict(to_sort_dict):
    sorted_dict = {}
    a = sorted(to_sort_dict)
    for i in range(len(a)):
        for k, v in to_sort_dict.items():
            if a[i] == k:
                v.sort()
                sorted_dict.update({k: v})

    return sorted_dict

#create 'this' router's message from .txt input        
def msg_data(my_router, routers):
    message = my_router[0] + ' ' + str(ord(my_router[0])) + ' '
    for i in range(len(routers)):
            message = message + ''.join(str(routers[i][j]) for j in range(len(routers[i]))) + ' '

    return message

#find minimum distance/cost
def min_dist(data, N):
    x = float('inf')
    for k, v in data.items():
        if k not in N:
            if v[0] < x:
                x = v[0]
    return x

#Dijkstra's Algorithm
def Dijkstras_Algorithm(data_list, my_router):
    #dict in form {'router(w/v)': [D(w/v),p(w/v)]}
    Dijkstra = {}
    set_N = [my_router[0]]
    infi = float('inf')

    #N is the step number
    N = 0
    while N < len(data_list):
        #initialisation
        if N == 0:
            for k in data_list.keys():
                if k == my_router[0]:
                    for i in range(len(data_list[k])):
                        if data_list[k][i][0] in data_list.keys():
                            Dijkstra.update({data_list[k][i][0]:\
                                             [data_list[k][i][1], my_router[0]]})
            
            for k in data_list.keys():
                if k != my_router[0] and k not in Dijkstra.keys():
                    Dijkstra.update({k:[infi, infi]})
        #loop
        else:
            #find w not in N' where D(w) is a minimum
            #add w to N'
            for k in Dijkstra.keys():
                if k not in set_N:
                    if min_dist(Dijkstra, set_N) == Dijkstra[k][0]:
                        set_N.append(k)
                        break
            #update D(v) for all v adjacent to w and not in N'
            k = set_N[N]
            for D_k in Dijkstra.keys():
                for i in range(len(data_list[k])):
                    #for all v
                    if D_k == data_list[k][i][0]:
                        #temp = sum distance
                        temp = Dijkstra[k][0] + data_list[k][i][1]
                        #if sum < D(v), update [D(v),p(v)]
                        if temp < Dijkstra[D_k][0]:
                            Dijkstra[D_k][0] = temp
                            Dijkstra[D_k][1] = k                        
        #increment step    
        N += 1
    return Dijkstra

#function to send and propagate data 'this' router has stored/recieved
#function is to stop sending/propagating messages if all messages have
#being ACKed by all routers, aka. all routers have recieved message once
def main_send(neighbours, recv_list, ACK_list, my_router):
    for k, v in neighbours.items():
        for i in range(len(recv_list)):
            r_temp = recv_list[i].split()
            r_temp[0] = int(r_temp[0])
            #propagate message if original message isn't from reciever
            if r_temp[0] != ord(k):
                s_msg = ''
                s_msg = my_router[0] + ' ' + recv_list[i]
                if k not in ACK_list.keys():
                    #send if neighbour router(k) hasn't ACKed at all
                    sender(v, s_msg)
                else:
                    if r_temp[0] not in ACK_list[k]:
                        #send if a message (number) hasn't being ACKed
                        sender(v, s_msg)

#function to transmit and recieve for this router    
def main_recv(my_router, neighbours, ACK_list, my_ACK, recv_list, serverSocket, OK_list, BAD_list):
    #Every second send/propergate routers' data
    sec = time.time()
    main_send(neighbours, recv_list, ACK_list, my_router)
        
    #reset my neighbour routers' condition counter      
    for k in OK_list.keys():
        OK_list[k] = 0

    while (time.time() - sec) < UPDATE_INTERVAL:
        sec_2 = time.time()
        #Every 0.2 sec send a hearbeat message 
        for k in neighbours.keys():
            ok_msg = '//OK ' + my_router[0]
            sender(neighbours[k], ok_msg)
        #within each 0.2 sec frame
        while (time.time() - sec_2) < HEARTBEAT_INTERVAL:
            #open server socket to recieve
            try:
                message, addr = serverSocket.recvfrom(2048)
                r_message = message.decode('utf-8')
                data_s = r_message.split()
                #case 'Heartbeat' message
                if data_s[0] == "//OK":
                    #increment router's counter
                    OK_list[data_s[1]] += 1
                #case disconnected routers in topology information
                elif data_s[0] == "//BAD":
                    #update list of disconnected routers
                    BAD_list = data_s[1:]
                #case ACK message
                elif data_s[0] == '#ACK':
                    #change str to int
                    for i in range(len(data_s)-2):
                        data_s[i+2] = int(data_s[i+2])
                    #update ACK_list    
                    if data_s[1] not in ACK_list.keys():
                        ACK_list.update({data_s[1]: data_s[2:]})
                    else:
                        if data_s[2:] != ACK_list[data_s[1]]:
                            ACK_list[data_s[1]] = data_s[2:]
                #case data messages
                else :
                    #update list of recieved messages
                    if r_message[2:] not in recv_list:
                        recv_list.append(r_message[2:])
                        #list of ACKed messages
                        my_ACK.append(data_s[1])
                        #send to all neighbours an ACK msg for data#(s) recieved
                        #ACK setup is cumulative
                        for k in neighbours.keys():
                            ack_msg = '#ACK ' + my_router[0] + ' '\
                                      + ' '.join(x for x in my_ACK)
                        
                            sender(neighbours[k], ack_msg)
                
            except timeout:
                continue
            
    #check for disconnections            
    for k in OK_list.keys():
        #if less than 3 hearbeat messages were recieved
        if OK_list[k] < 3:
            #add to disconnected router list(BAD_list)
            if k not in BAD_list:
                BAD_list.append(k)
        else:
            #if previous router was disconnected but now is 'alive'
            if k in BAD_list:
                BAD_list.remove(k)
                #send data information to the newly connected router
                for i in range(len(recv_list)):
                    s_msg = ''
                    s_msg = my_router[0] + ' ' + recv_list[i]
                    sender(neighbours[k], s_msg)
                    
    #if 'I' am in BAD_list(disconnected/not running)                
    if my_router[0] in BAD_list:
        BAD_list.remove(my_router[0])
        
    #Send current known disconnected routers
    for key in neighbours.keys():
        bad_msg = '//BAD ' + ' '.join(x for x in BAD_list)
        sender(neighbours[key], bad_msg)
        
    return ACK_list, recv_list, OK_list, BAD_list

#function to print Dijkstra result in required format
def print_dijkstra(Dijkstra_table):
    print()
    print(f'I am router {my_router[0]}')
    for k in Dijkstra_table:
        path = ''
        goal = k
        while goal != my_router[0]:
            #p is predecessor
            p = Dijkstra_table[goal][1]
            path = p + path
            goal = p
        path = path + k
        print(f'Least cost path to router {k}:{path} and the cost is ',\
              '{:.1f}'.format(Dijkstra_table[k][0]))
    

if __name__ == "__main__":
    #only when 3 arguments are entered in the right format
    if len(sys.argv) != 2:
        print(f'ERROR: you have entered {len(sys.argv)} arguments.')
        print('requried format: $python3 Lsr.py filename.txt')
    else:
        #initialisation of some dicts and lists
        #pipelined ACK procedure
        ACK_list = {}
        my_ACK = []

        #recieved data messages
        recv_list = []

        #Heartbeat procedure
        OK_list = {}
        BAD_list = []

        #read file input
        routers, neighbours, my_router = read_txt(sys.argv[1])
        #UDP(type SOCK_DGRAM) reciever socket initialise
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        serverSocket.bind(('localhost', my_router[1]))
        serverSocket.settimeout(HEARTBEAT_INTERVAL)
        #my router's message
        msg = msg_data(my_router, routers)
        #initialise my data_list(router map data)
        data_list = {my_router[0]:routers}
        #my router message is first element of recieved data
        recv_list.append(msg[2:])
        #populate OK_list dict with neighbour routers to check for 'alive' status
        for k in neighbours.keys():
            OK_list.update({k: 0})

        #infinite loop
        while 1:
            curr_time = time.time()
            #before 30 sec have lapsed
            while (time.time() - curr_time) < ROUTE_UPDATE_INTERVAL:
                #operate main_recv() function to transmit and recieve all data
                ACK_list, recv_list, OK_list, BAD_list = \
                           main_recv(my_router, neighbours, ACK_list, my_ACK, recv_list, serverSocket, OK_list, BAD_list)

            #every 30 sec update and organise data list of entire network topology
            for i in range(len(recv_list)):
                data_temp = recv_list[i].split()
                data_temp[0] = int(data_temp[0])
                if chr(data_temp[0]) not in data_list.keys():
                    for j in range(len(data_temp)-1):
                        data_temp[j+1] = [data_temp[j+1][0], float(data_temp[j+1][1:])]
                    data_list.update({chr(data_temp[0]):data_temp[1:]})

            #deep copy dict(data_list) to use for Dijkstra's Algorithm
            data_list_copy = copy.deepcopy(data_list)
            #remove routers from data list(copy) if they are disconnected at the moment
            for i in range(len(BAD_list)):
                if BAD_list[i] in data_list_copy.keys():
                    removed_key = data_list_copy.pop(BAD_list[i])
            #sort the data list (unnecessary step but easier to read during debugging)
            data_list_sorted = sort_dict(data_list_copy)
            #Apply Duhjstra's Algorithm
            Dijkstra_table = Dijkstras_Algorithm(data_list_sorted, my_router)
            #print result
            print_dijkstra(Dijkstra_table)
                
            

    
                
                        
                
                

            
        

                        
