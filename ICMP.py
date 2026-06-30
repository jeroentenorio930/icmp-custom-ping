from socket import *
import os
import sys
import struct
import time
import select
import binascii

ICMP_ECHO_REQUEST = 8

def checksum(string):

    csum = 0
    countTo = (len(string) // 2) * 2
    count = 0

    while count < countTo:
        thisVal = string[count+1] * 256 + string[count] #removed ord
        csum = csum + thisVal
        csum = csum & 0xffffffff
        count = count + 2
    if countTo < len(string):
        csum = csum + string[len(string) - 1] # removed ord 
        csum = csum & 0xffffffff

    csum = (csum >> 16) + (csum & 0xffff)
    csum = csum + (csum >> 16)
    answer = ~csum
    answer = answer & 0xffff
    answer = answer >> 8 | (answer << 8 & 0xff00)
    return answer
    
def receiveOnePing(mySocket, ID, timeout, destAddr):

    timeLeft = timeout

    while 1:
        startedSelect = time.time()
        whatReady = select.select([mySocket], [], [], timeLeft)
        howLongInSelect = (time.time() - startedSelect)

         # Timeout
        if whatReady[0] == []:
            return "Request timed out."
        
        timeReceived = time.time()
        recPacket, addr = mySocket.recvfrom(1024)

        #Fill in start
        #Fetch the ICMP header from the IP packet
        # 160/8 = 20, so the start of the header is at byte 20
        # type (1), code (1), checksum (2), ID(2), sequence (2) <-- given ni miss
        type, code, checksum, id, sequence = struct.unpack("bbHHh", recPacket[20:28])

        # Type and code must be set to 0.
        # ICMP Error Parsing (+1) -  Parse and display ICMP error codes 
        # (e.g., Destination Network/Host Unreachable, TTL Expired) 
        # when Echo Reply is not received. 
        # https://www.iana.org/assignments/icmp-parameters/icmp-parameters.xhtml#icmp-parameters-codes-3  
        if type == 3:
            if code == 0:
                return f"[Err] Destination Network Unreachable (Type {type}, Code {code})"
            elif code == 1:
                return f"[Err] Destination Host Unreachable (Type {type}, Code {code})"
            elif code == 2:
                return f"[Err] Destination Protocol Unreachable (Type {type}, Code {code})"
            elif code == 3:
                return f"[Err] Destination Port Unreachable (Type {type}, Code {code})"
            elif code == 4:
                return f"[Err] Fragmentation Needed and Don't Fragment was Set (Type {type}, Code {code})"
            elif code == 5:
                return f"[Err] Source Route Failed (Type {type}, Code {code})"
            elif code == 6:
                return f"[Err] Destination Network Unknown (Type {type}, Code {code})"
            elif code == 7:
                return f"[Err] Destination Host Unknown (Type {type}, Code {code})"
            elif code == 8:
                return f"[Err] Source Host Isolated (Type {type}, Code {code})"
            elif code == 9:
                return f"[Err] Network Administratively Prohibited (Type {type}, Code {code})"
            elif code == 10:
                return f"[Err] Host Administratively Prohibited (Type {type}, Code {code})"
            elif code == 11:
                return f"[Err] Network Unreachable for TOS (Type {type}, Code {code})"
            elif code == 12:
                return f"[Err] Host Unreachable for TOS (Type {type}, Code {code})"
            elif code == 13:
                return f"[Err] Communication Administratively Prohibited (Type {type}, Code {code})"
            elif code == 14:
                return f"[Err] Host Precedence Violation (Type {type}, Code {code})"
            elif code == 15:
                return f"[Err] Precedence cutoff in effect (Type {type}, Code {code})"
        elif type == 5:
            if code == 0:
                return f"[Err] Redirect Datagram for the Network (Type {type}, Code {code})"
            elif code == 1:
                return f"[Err] Redirect Datagram for the Host (Type {type}, Code {code})"
            elif code == 2:
                return f"[Err] Redirect Datagram for the TOS and Network (Type {type}, Code {code})"
            elif code == 3:
                return f"[Err] Redirect Datagram for the TOS and Host (Type {type}, Code {code})"
        elif type == 11:
            if code == 0:
                return f"[Err] TTL Exceeded in Transit (Type {type}, Code {code})"
            elif code == 1:
                return f"[Err] TTL Exceeded in Reassembly (Type {type}, Code {code})"
        elif type == 12:
            if code == 0:
                return f"[Err] Parameter Problem: Pointer indicates the error (Type {type}, Code {code})"
            elif code == 1:
                return f"[Err] Parameter Problem: Missing a required option (Type {type}, Code {code})"
            elif code == 2:
                return f"[Err] Parameter Problem: Bad Length (Type {type}, Code {code})"
        if ID != id:
            return f"[Err] Expected id={ID}, but got id={id}"
        
        if type == 0:
            if id != ID:
                continue 
            
            bytesInDouble = struct.calcsize("d")
            timeSent = struct.unpack("d", recPacket[28:28 + bytesInDouble])[0]
            
            # Return the RTT
            return timeReceived - timeSent
        
        #Fill in end
        
        timeLeft = timeLeft - howLongInSelect
        if timeLeft <= 0:
            return "Request timed out."

def sendOnePing(mySocket, destAddr, ID):

    # Header is type (8), code (8), checksum (16), id (16), sequence (16)
    myChecksum = 0
    # Make a dummy header with a 0 checksum
    
    # struct -- Interpret strings as packed binary data
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    data = struct.pack("d", time.time())

    # Calculate the checksum on the data and the dummy header.
    # removed str() since header + data is a byte object in Python 3
    myChecksum = checksum(header + data)

    # Get the right checksum, and put in the header
    if sys.platform == 'darwin':
        # Convert 16-bit integers from host to network byte order
        myChecksum = htons(myChecksum) & 0xffff
    else:
        myChecksum = htons(myChecksum)
    
    header = struct.pack("bbHHh", ICMP_ECHO_REQUEST, 0, myChecksum, ID, 1)
    packet = header + data
    mySocket.sendto(packet, (destAddr, 1)) # AF_INET address must be tuple, not str
    # Both LISTS and TUPLES consist of a number of objects
    # which can be referenced by their position number within the object.

def doOnePing(destAddr, timeout):

    icmp = getprotobyname("icmp")
    # SOCK_RAW is a powerful socket type. For more details: http://sockraw.org/papers/sock_raw
    
    #Fill in start
    
    #create socket
    mySocket = socket(AF_INET, SOCK_RAW, icmp)
    
    #Fill in end
   
    myID = os.getpid() & 0xFFFF # Return the current process i
    
    #Fill in start
    
    #send a single ping using the socket, dst addr and ID
    sendOnePing(mySocket, destAddr, myID)
    
    #add delay using timeout
    delay = receiveOnePing(mySocket, myID, timeout, destAddr)
    
    #close socket
    mySocket.close()
   
   #Fill in end
    
    return delay
    
def ping(host, timeout=2):

    # timeout=1 means: If one second goes by without a reply from the server,
    # the client assumes that either the client's ping or the server's pong is lost
    
    dest = gethostbyname(host)
    print("Pinging " + dest + " using Python (Ctrl+C to end):")
    print("")

    # 1. RTT Summary Stats (+1) - At the end of the ping session, 
    # display the minimum, maximum, and average RTT values, and 
    # calculate the packet loss rate as a percentage.
    rtts = []
    pckts_sent = 0
    pckts_lost = 0 
    
    # Send ping requests to a server separated by approximately one second
    try: 
        while 1 :
            pckts_sent += 1
            delay = doOnePing(dest, timeout)

            if isinstance(delay, float):
                rtt_ms = delay * 1000
                rtts.append(rtt_ms)
                print(f"Reply from {dest}: time={rtt_ms:.2f}ms")
            else:
                pckts_lost += 1
                print(delay)
            
            time.sleep(1)# one second
    except KeyboardInterrupt:
        print("")
        if pckts_sent > 0:
            loss_rate = (pckts_lost / pckts_sent) * 100
            print(f"Packets sent: {pckts_sent}, packets received: {pckts_sent - pckts_lost}, {loss_rate:.2f}% packet loss")

        if rtts:
            print(f"RTT min: {min(rtts):.2f}ms, RTT avg: {sum(rtts) / len(rtts):.2f}ms, RTT max: {max(rtts):.2f}ms")
        
        else:
            print("No replies received.")
    return delay

if __name__ == '__main__':
    if len(sys.argv) > 1:
            host = sys.argv[1]
    else:
        host = input("Enter target host: ")
            
    ping(host)

    