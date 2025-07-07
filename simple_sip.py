#!/usr/bin/env python3
"""
Simple SIP client to make calls using socket programming
"""
import socket
import time
import random

class SimpleSIPClient:
    def __init__(self, server_host='192.168.1.187', server_port=5060, 
                 username='1001', password='tt55oo77'):
        self.server_host = server_host
        self.server_port = server_port
        self.username = username
        self.password = password
        self.local_port = random.randint(5060, 6000)
        self.call_id = f"{random.randint(1000000, 9999999)}@{socket.gethostname()}"
        self.tag = f"tag{random.randint(1000, 9999)}"
        self.branch = f"z9hG4bK{random.randint(1000000, 9999999)}"
        
    def create_invite_message(self, to_number):
        """Create SIP INVITE message"""
        local_ip = self.get_local_ip()
        
        sip_message = f"""INVITE sip:{to_number}@{self.server_host} SIP/2.0
Via: SIP/2.0/UDP {local_ip}:{self.local_port};branch={self.branch}
Max-Forwards: 70
From: <sip:{self.username}@{self.server_host}>;tag={self.tag}
To: <sip:{to_number}@{self.server_host}>
Contact: <sip:{self.username}@{local_ip}:{self.local_port}>
Call-ID: {self.call_id}
CSeq: 1 INVITE
Content-Type: application/sdp
Content-Length: 0

"""
        return sip_message.replace('\n', '\r\n').encode()

    def get_local_ip(self):
        """Get local IP address"""
        try:
            # Connect to a remote server to determine local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    def make_call(self, to_number):
        """Make a SIP call"""
        try:
            # Create UDP socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', self.local_port))
            sock.settimeout(10)
            
            print(f"Making call from {self.username} to {to_number}")
            print(f"Using server: {self.server_host}:{self.server_port}")
            
            # Send INVITE
            invite_msg = self.create_invite_message(to_number)
            print("Sending INVITE message...")
            sock.sendto(invite_msg, (self.server_host, self.server_port))
            
            # Wait for response
            try:
                response, addr = sock.recvfrom(1024)
                print(f"Received response from {addr}:")
                print(response.decode())
                
                if b"200 OK" in response:
                    print("Call connected successfully!")
                    # Here you would handle the media session
                    time.sleep(5)  # Simulate call duration
                    print("Call ended")
                elif b"407 Proxy Authentication Required" in response or b"401 Unauthorized" in response:
                    print("Authentication required - need to implement SIP authentication")
                else:
                    print("Call failed or requires authentication")
                    
            except socket.timeout:
                print("No response received - timeout")
                
        except Exception as e:
            print(f"Error making call: {e}")
        finally:
            sock.close()

def main():
    """Test the SIP client"""
    # Try both IP addresses
    for server_ip in ['192.168.1.187', '149.200.251.12']:
        print(f"\n--- Trying server: {server_ip} ---")
        client = SimpleSIPClient(
            server_host=server_ip,
            server_port=5060,
            username='1001',
            password='tt55oo77'
        )
        
        # Make a call to the number
        client.make_call('0790002033')
        
        time.sleep(2)  # Wait between attempts

if __name__ == "__main__":
    main()
