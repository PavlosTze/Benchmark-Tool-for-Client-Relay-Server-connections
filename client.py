import socket
import sys
import subprocess
import re
import threading
import argparse
import urllib2
from timeit import default_timer
import errno

global ping_ClientServer;
ping_ClientServer = 0;
global numHops_ClientServer;
numHops_ClientServer = 0;
global ping_ClientRelay;
ping_ClientRelay = 0;
global numHops_ClientToRelay;
numHops_ClientToRelay = 0;


# Calculation of average ping at Client -> End server
def calcAvgPing(hostnameToPing):
    global ping_ClientServer;
    threadLock.acquire()
    p1 = subprocess.Popen(['ping', '-c 1', '-W 3', hostnameToPing], stdout=subprocess.PIPE)
    output = p1.communicate()[0]
    if "100% packet loss" in output:
        ping_ClientServer = -1;
    else:
        output = output.split('\n')[-2:]
        match = re.search('([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)', output[0])
        ping_avg = float(match.group(2))
        ping_ClientServer += float(ping_avg)      
    threadLock.release()
    
    
# Calculation of average ping at Client -> Relay Node
def calcAvgPingToRelay(hostnameToPing):
    global ping_ClientRelay;
    threadLock.acquire()
    p1 = subprocess.Popen(['ping', '-c 1', '-W 3', hostnameToPing], stdout=subprocess.PIPE)
    output = p1.communicate()[0]
    if "100% packet loss" in output:
        ping_ClientRelay = -1;
    else:
        output = output.split('\n')[-2:]
        match = re.search('([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)/([\d]*\.[\d]*)', output[0])
        ping_avg = float(match.group(2))
        ping_ClientRelay += float(ping_avg)
    threadLock.release()
    
    
# Calculate number of hops until end server
def calcNumHops(hostnameToPing):
    global numHops_ClientServer;
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
        numHops_ClientServer = number -1;
    else:
        numHops_ClientServer = -1

        
# Calculate number of hops until relay
def calcNumHopsToRelay(hostnameToPing):
    global numHops_ClientToRelay;
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
        numHops_ClientToRelay = number -1;
    else:
        numHops_ClientToRelay = -1
        
try:

    start = default_timer()
    BUFFER_SIZE = 1024
    parser = argparse.ArgumentParser()

    parser.add_argument('-e', type=argparse.FileType('r'))
    parser.add_argument('-r', type=argparse.FileType('r'))
                    
    results = parser.parse_args()
    
    # If the program has the correct arguments as input to run
    if bool(results.e) ^ bool(results.r):
        parser.error('-e end servers text file and -r relay nodes text file must be given together')
        sys.exit()

    aliasFound = 0;
    endServ = [];
    relayServ = [];
    ipRelays = [];
    portRelays = [];
    pingThroughRelays = {};
    numHopsThroughRelays = {};
    nameOfBestMethod = ''
    pckLossAction = 'nothing'

    # We get the End Servers as a list of strings
    for line in results.e:
        hostname = line.split("\n")
        
        endServString = hostname[0];
        
        endServ.append(endServString); 
        
        
    # We get the Relay Nodes as a list of strings
    for line in results.r:
        hostname = line.split("\n")
        
        relayString = hostname[0];
        
        relayServ.append(relayString);
        
        
    for name in relayServ:
        rName = name.split(",")
        
        ip = rName[1];
        port = rName[2];
        
        ipRelays.append(ip);
        portRelays.append(port);
        
    
    # Checking user input
    aliasInput = raw_input("Give an alias of an end server, benchmarking method and number of iterations: ")
    info = aliasInput.split(" ")
    
    for name in endServ:
        if info[0] in name:
            host = name.split(",")
            aliasFound = 1;
    
    if info[0] == "exit":
            sys.exit()
    
    while not (info[1].isdigit() and (info[2] == "latency" or info[2] == "numHops") and aliasFound == 1):
        print >>sys.stderr, '\nWrong input. Try again or type "exit" to terminate the program.'
        aliasInput = raw_input("Give an alias of an end server, benchmarking method and number of iterations: ")
        info = aliasInput.split(" ")
        
        if info[0] == "exit":
            sys.exit()
            
        for name in endServ:
            if info[0] in name:
                host = name.split(",")
                aliasFound = 1;

    numOfChecks = int(info[1]);
    
    #Calculate latency-ping and numHops Direct Client-End Server
    threadLock = threading.Lock()
    threads = []
    for i in range(numOfChecks):
        t = threading.Thread(target = calcAvgPing, args = (host[0],))
        t.setDaemon(True)
        threads.append(t)
        t.start()

    for i in range(numOfChecks):
        threads[i].join();
    
    
    calcNumHops(host[0])
    avgPingClSer = float(ping_ClientServer)/numOfChecks
    
    #Calculate latency-ping and numHops Client-Relay Server
    for i, ip in enumerate(ipRelays):

        threadLock = threading.Lock()
        threads = []
        for j in range(numOfChecks):
            t = threading.Thread(target = calcAvgPingToRelay, arg s= (ip,))
            t.setDaemon(True)
            threads.append(t)
            t.start()

        for j in range(numOfChecks):
            threads[j].join();
        
        pingThroughRelays[ip] = ping_ClientRelay
        ping_ClientRelay = 0;

        calcNumHopsToRelay(ip)
        
        numHopsThroughRelays[ip] = numHops_ClientToRelay
        numHops_ClientToRelay = -5;

        MESSAGE = 'ping:{}:{}'.format(numOfChecks, host[0])
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            s.connect((ip, 1048))
        except socket.error, v:
            errorcode=v[0]
            if errorcode==errno.ECONNREFUSED:
                print "\nCONNECTION REFUSED to relay. Make sure relay is running and restart program"
                sys.exit()
            
        s.send(MESSAGE)
        
        data1 = s.recv(BUFFER_SIZE)
        s.close()

        dataFromRelay = data1.split(":")

        pingThroughRelays[ip] = float(pingThroughRelays[ip])/numOfChecks
        
        if float(dataFromRelay[0]) == -1:
            pingThroughRelays[ip] = -1;
        else:
            pingThroughRelays[ip] += float(dataFromRelay[0])
        
        if dataFromRelay[1] == 'TIMEOUT':
            numHopsThroughRelays[ip] = -5;
        else:
            numHopsThroughRelays[ip] += int(dataFromRelay[1])
        
        print "received data:", data1

    numHops_ClientServer += 1;     
        
        
    # Print benchmarking results
    if info[2] == 'latency':
        print "\nYou chose as first criterion: Ping RTT"
        
        if float(ping_ClientServer) == -1:
            print "100% packet loss from: " + host[0]
        else:
            print '\nAverage Ping RTT Direct Mode From Client to Server: ' + host[0]
            print avgPingClSer;
            
            print '\nAverage Ping RTT Through Relay {} to End Server: {}'.format(ipRelays[0], host[0])
            print pingThroughRelays[ipRelays[0]];
            
            print '\nAverage Ping RTT Through Relay {} to End Server {}: '.format(ipRelays[1], host[0])
            print pingThroughRelays[ipRelays[1]];
        
        if numHops_ClientServer < 0:
            print '\nServer timeout when counting hops to End Server: ' + host[0]
        else:
            print '\nAverage NUMBER OF HOPS at Direct Mode From Client to Server: ' + host[0]
            print numHops_ClientServer  
            
        if numHopsThroughRelays[ipRelays[0]] < 0:
            print '\nServer {} timeout when counting hops through Relay: {}'.format(host[0],ipRelays[0])
        else:
            print '\nAverage NUMBER OF HOPS From Client through {} to End Server {}: '.format(ipRelays[0],host[0])
            print numHopsThroughRelays[ipRelays[0]]     
            
        if numHopsThroughRelays[ipRelays[1]] < 0:
            print '\nServer {} timeout when counting hops through Relay: {}'.format(host[0],ipRelays[1])
        else:
            print '\nAverage NUMBER OF HOPS From Client through {} to End Server {}: '.format(ipRelays[1],host[0])
            print numHopsThroughRelays[ipRelays[1]]       
    elif info[2] == 'numHops':
        print "\nYou chose as first criterion: Number of Hops"
        
        if numHops_ClientServer < 0:
            print '\nServer timeout when counting hops to End Server: ' + host[0] 
        else:
            print '\nAverage NUMBER OF HOPS at Direct Mode From Client to Server: ' + host[0]
            print numHops_ClientServer  
            
        if numHopsThroughRelays[ipRelays[0]] < 0:
            print '\nServer {} timeout when counting hops through Relay: {} '.format(host[0],ipRelays[0])
        else:
            print '\nAverage NUMBER OF HOPS From Client through {} to End Server {}: '.format(ipRelays[0],host[0])
            print numHopsThroughRelays[ipRelays[0]]     
            
        if numHopsThroughRelays[ipRelays[1]] < 0:
            print '\nServer {} timeout when counting hops through Relay: {} '.format(host[0],ipRelays[1])
        else:
            print '\nAverage NUMBER OF HOPS From Client through {} to End Server {}: '.format(ipRelays[1],host[0])
            print numHopsThroughRelays[ipRelays[1]]
              
        if float(ping_ClientServer) == -1:
            print "100% packet loss from: " + host[0]
        else:
            print '\nAverage Ping RTT Direct Mode From Client to Server: ' + host[0]
            print avgPingClSer;
            
            print '\nAverage Ping RTT Through Relay {} to End Server: {}'.format(ipRelays[0], host[0])
            print pingThroughRelays[ipRelays[0]];
            
            print '\nAverage Ping RTT Through Relay {} to End Server {}: '.format(ipRelays[1], host[0])
            print pingThroughRelays[ipRelays[1]];
    else:
        print 'Unknown Error. Program terminated.'
        sys.exit()

    # If 100% packet loss is shown, ask the user what to do next
    if float(ping_ClientServer) == -1:
        print "\n100% packet loss from the end server.\nDo you want to exit the program, or continue downloading the file?"
        pckLossAction = raw_input("Type 'exit' for terminating, or type 'download' alternatively:   ")
        while not (pckLossAction == "exit" or pckLossAction == "download"):
            print "\n100% packet loss from the end server.\nDo you want to exit the program, or continue downloading the file?"
            pckLossAction = raw_input("Type 'exit' for terminating, or type 'download' alternatively:   \n")
            
        if pckLossAction == "exit":
            sys.exit();
    
    
    #Find minumum ping - best case
    minIndexPing = -1;
    equalPing = 'no';
    if  avgPingClSer > 0 and pingThroughRelays[ipRelays[0]] > 0 and pingThroughRelays[ipRelays[0]] > 0:
        min = avgPingClSer;
        
        for i, ip in enumerate(ipRelays):
            if pingThroughRelays[ip] < min:
                min = pingThroughRelays[ip]
                minIndexPing = i
                equalPing = 'no'
            elif pingThroughRelays[ip] == min and equalPing != 'no':
                equalPing = "{}={}".format(minIndexPing,i)
            elif numHopsThroughRelays[ip] == min and equalPing != 'no':
                equalPing += "={}".format(i)
    else:
        minIndexPing = -5;
        
    
    #Find minumum number of hops - best case
    minIndexHops = -1;
    equalHops = 'no';
    if  numHops_ClientServer > 0 and numHopsThroughRelays[ipRelays[0]] > 0 and numHopsThroughRelays[ipRelays[0]] > 0:
        min = numHops_ClientServer;

        for i, ip in enumerate(ipRelays):
            if numHopsThroughRelays[ip] < min:
                min = numHopsThroughRelays[ip]
                minIndexHops = i
                equalHops = 'no'
            elif numHopsThroughRelays[ip] == min and equalHops == 'no':
                equalHops = "{}={}".format(minIndexHops,i)
            elif numHopsThroughRelays[ip] == min and equalHops != 'no':
                equalHops += "={}".format(i)
    else:
        minIndexHops = -5;    
   

    url = raw_input("\nPlease input the URL of the file you want to download: ")
    if url == "exit":
            sys.exit();
    while not ((info[0] in url) or ("bbc.co.uk" in url) or ("japan.go.jp" in url)):
        print "\n\nWrong url, benchmark has run for a different server."
        url = raw_input("Please input the URL for the server you asked a benchmark before:  ")
        
        if url == "exit":
            sys.exit();
            
    # Printing information about what will happen next based on the benchmark      
    if info[2] == 'latency':
        if equalPing == 'no' and minIndexPing == -1:
            print "\nClient will direct download from the End Server as this is the fastest method.\n"
        elif equalPing == 'no' and minIndexPing>=0: 
            print "\nClient will download through a Relay Node {} as this is the fastest method.\n".format(ipRelays[minIndexPing])
        elif equalPing != 'no':
            print "\nTwo or more benchmarks have the same result. We will consider RTT."
        else:
            print "\nWe have 100% packet loss or timeout. Trying to download directly from the End Server."
    else:
        if equalHops == 'no' and minIndexHops == -1:
            print "\nClient will direct download from the End Server as this is the fastest method.\n"
        elif equalHops == 'no' and minIndexHops>=0: 
            print "\nClient will download through a Relay Node {} as this is the fastest method.\n".format(ipRelays[minIndexHops])
        elif equalHops != 'no':
            print "\nTwo or more benchmarks have the same result. We will consider RTT."
        else:
            print "\nWe have 100% packet loss or timeout. Trying to download directly from the End Server."
    

    # If benchmarks' results where equal
    if info[2] == 'latency' and equalPing != 'no':
        equal = equalPing.split("=")
        if equal[0] == '-1':
            mininumForEquals = numHops_ClientServer
        else:
            mininumForEquals = numHopsThroughRelays[ipRelays[int(equal[0])]]
        indexMininumForEquals = int(equal[0])
        equalPingHops = "no"
        for i,value in enumerate(equal):
            if int(value) == -1 and i>0:
                if numHops_ClientServer < mininumForEquals:
                    mininumForEquals = numHops_ClientServer
                    indexMininumForEquals = -1                  
                    equalPingHops = "no"
                elif numHops_ClientServer == mininumForEquals:       
                    equalPingHops = "yes"
            elif i>0:
                if numHopsThroughRelays[ipRelays[int(value)]] < mininumForEquals:
                    mininumForEquals = numHopsThroughRelays[ipRelays[int(value)]]
                    indexMininumForEquals = int(value)
                    equalPingHops = "no"
                elif numHopsThroughRelays[ipRelays[int(value)]] == mininumForEquals:
                    equalPingHops = "yes"
                
        if equalPingHops == "yes":
            print "We have the equal results both for pings and number of hops so we will choose randomly."
        else:
            if indexMininumForEquals == -1:
                print "Based on the number of hops (as based on pings the benchmarks gave equal results), the most fast way is to access the End Server directly."
            else:
                print "Based on the number of hops (as based on pings the benchmarks gave equal results), the most fast way is "
                print "the one through Relay Node {} so we will choose that.".format(ipRelays[indexMininumForEquals])               
    elif info[2] == 'numHops' and equalHops != 'no':
        equal = equalHops.split("=")
        if equal[0] == '-1':
            mininumForEquals = avgPingClSer
        else:
            mininumForEquals = pingThroughRelays[ipRelays[int(equal[0])]]
        indexMininumForEquals = int(equal[0])
        equalPingHops = "no"
        for i,value in enumerate(equal):
            if int(value) == -1 and i>0:
                if avgPingClSer < mininumForEquals:
                    mininumForEquals = avgPingClSer
                    indexMininumForEquals = -1                  
                    equalPingHops = "no"
                elif avgPingClSer == mininumForEquals:       
                    equalPingHops = "yes"
            elif i>0:
            
                print pingThroughRelays[ipRelays[int(value)]]
                if pingThroughRelays[ipRelays[int(value)]] < mininumForEquals:
                    mininumForEquals = pingThroughRelays[ipRelays[int(value)]]
                    indexMininumForEquals = int(value)
                    equalPingHops = "no"
                elif pingThroughRelays[ipRelays[int(value)]] == mininumForEquals:
                    equalPingHops = "yes"
                    
                          
        if equalPingHops == "yes":
            print "We have the equal results both for pings and number of hops so we will choose randomly."
        else:
            if indexMininumForEquals == -1:
                print "Based on the RTT (as based on number of hops the benchmarks gave equal results), the most fast way is to access the End Server directly."
            else:
                print "Based on the RTT (as based on number of hops the benchmarks gave equal results), the most fast way is "
                print "the one through Relay Node {} so we will choose that.".format(ipRelays[indexMininumForEquals])
    
    if pckLossAction == "download" or (info[2] == 'latency' and equalPing == 'no' and minIndexPing == -1) or (info[2] == 'numHops' and equalHops == 'no' and minIndexHops == -1):
        file = url.split("/")    
        start = default_timer()
        response = urllib2.urlopen(url)
        sourceToFile = response.read()
        duration = default_timer() - start
        duration = round(duration,7)
        print "\nIt took " + str(duration) + " seconds for the downloading of the file."
        htmlSource = response.info()   
        type = htmlSource['content-type'].split("/")  
        fh = open(file[-1], "w")
        fh.write(sourceToFile)        
        response.close()
        fh.close()  
        
finally:
    duration = default_timer() - start
    duration = round(duration,7)
    print "\n\nProgram ran for: " + str(duration) + " seconds."
    print >>sys.stderr, '\nPROGRAM TERMINATED\n'

