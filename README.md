# Benchmark Tool for Client-Relay-Server connections

A benchmark tool that takes as input a server IP, and benchmarks different routes from the client to the server, using either direct connection either Relay Nodes, based on RTT (Round Trip Time) and Number of Hops. As a final step, we can download a file from that server using the fastest way based on the benchmark results.  
  
**How to run using command line:**  
python client.py -e end_servers.txt -r relay_nodes.txt

Where end_servers.txt is in the format of *'Domain Address, alias'*:    
www.google.com, google  
www.github.com, github  
...  
  
and relay_nodes.txt is in the format of *'alias, IP Address, port number'*:   
my_relay1, 18.18.18.18 , 1025  
my_relay2, 118.118.118.118 , 1026  
...  


Then the client will ask for the alias of the end server that we want to benchmark, the number of iterations and the benchmark method, accepted answers for the benchmark method is either ***latency*** either ***numHops***.  

After the benchmark is done, the client will ask for the file that we wanted to download from the end server, and will download it using the fastest route possible (using the results of the benchmark).
