import socket
import sys
import subprocess
import re
import threading

global ping_RelayServer;
ping_RelayServer = 0;
global numHops_RelayServer;
numHops_RelayServer = 0;


# Calculation of average ping at Relay node -> End server
def calcAvgPing(hostnameToPing):
    global ping_RelayServer;
    threadLock.acquire()
    p1 = subprocess.Popen(['ping', '-c 1', '-W 3', hostnameToPing], stdout=subprocess.PIPE)
    output = p1.communicate()[0]
    if "100% packet loss" in output:
        ping_RelayServer = -1;
    else:
        output = output.split('\n')[-2:]
        match = re.search('([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)', output[0])
        ping_avg = float(match.group(2))
        ping_RelayServer += float(ping_avg)
    threadLock.release()
       
# Calculation of number of hops until end server
def calcNumHops(hostnameToPing):
    global numHops_RelayServer;
    number = 0
    p1 = subprocess.Popen(["traceroute", hostnameToPing], stdout=subprocess.PIPE)
    while 1:
        strLine = p1.stdout.readline()
        if not strLine: 
            break
        else:
            if '* * *' in strLine:
                number = -1
                break
            else:
                number += 1;
                
    if number > 0:
        numHops_RelayServer = number -1;
    else:
        numHops_RelayServer = -1  

RECV_BUFFER_SIZE = 1024 

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to the port

#By setting the host name to the empty string, it tells the bind() method to fill in the address of the current machine.

server_address = ('', 1048)
print >>sys.stderr, 'starting up on %s port %s' % server_address
sock.bind(server_address)

# Listen for incoming connections
sock.listen(1)

while True:
    # Wait for a connection
    print >>sys.stderr, 'waiting for a connection'
    connection, client_address = sock.accept()

    try:
        print >>sys.stderr, 'connection from', client_address

        # Receive the data in small chunks and retransmit it
        while True:
            data = connection.recv(RECV_BUFFER_SIZE)
            print >>sys.stderr, 'received "%s"' % data
            if data:
                ping_RelayServer = 0;
                data = data.split(":")
                endServer = data[2];
                numOfCheck = int(data[1]);
                if data[0] == "ping":
                    threadLock = threading.Lock()
                    threads = []
                    for i in range(numOfCheck):
                        t = threading.Thread(target=calcAvgPing, args=(endServer,) )
                        t.setDaemon(True)
                        threads.append(t)
                        t.start()

                    for i in range(numOfCheck):
                        threads[i].join();
                    
                    calcNumHops(endServer)
                
                if ping_RelayServer == -1:
                    avgPingToServ = -1;
                    print '\n\n100% packet loss from Server: ' + endServer
                else:
                    avgPingToServ = float(ping_RelayServer)/numOfCheck;
                    print '\n\nAverage Ping RTT From Relay to Server: ' + endServer
                    print avgPingToServ
            
                if numHops_RelayServer < 0:
                    print '\nServer timeout when counting hops to End Server.'
                    MESSAGE = '{}:{}'.format(avgPingToServ,'TIMEOUT')
                else:
                    print '\nAverage NUMBER OF HOPS From Relay to Server: ' + endServer
                    print numHops_RelayServer
                    MESSAGE = '{}:{}'.format(avgPingToServ,numHops_RelayServer)  

                connection.sendall(MESSAGE)
            else:
                print >>sys.stderr, 'no more data from', client_address
                break
            
    finally:
        # Clean up the connection
        connection.close()