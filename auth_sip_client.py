#!/usr/bin/env python3
"""
SIP client with digest authentication support
"""
import socket
import time
import random
import hashlib
import re

class AuthenticatedSIPClient:
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
        self.cseq = 1
        
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "127.0.0.1"

    def parse_auth_header(self, auth_header):
        """Parse WWW-Authenticate header"""
        auth_info = {}
        # Extract values using regex
        patterns = {
            'realm': r'realm="([^"]*)"',
            'nonce': r'nonce="([^"]*)"',
            'opaque': r'opaque="([^"]*)"',
            'algorithm': r'algorithm=([^,\s]*)',
            'qop': r'qop="([^"]*)"'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, auth_header)
            if match:
                auth_info[key] = match.group(1)
        
        return auth_info

    def calculate_digest_response(self, auth_info, method, uri):
        """Calculate digest response for authentication"""
        username = self.username
        password = self.password
        realm = auth_info.get('realm', '')
        nonce = auth_info.get('nonce', '')
        qop = auth_info.get('qop', '')
        
        # Calculate HA1
        ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
        
        # Calculate HA2
        ha2 = hashlib.md5(f"{method}:{uri}".encode()).hexdigest()
        
        # Calculate response
        if qop:
            nc = "00000001"
            cnonce = f"{random.randint(100000, 999999)}"
            response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()).hexdigest()
            return response, nc, cnonce
        else:
            response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()
            return response, None, None

    def create_invite_with_auth(self, to_number, auth_info=None):
        """Create SIP INVITE message with optional authentication"""
        local_ip = self.get_local_ip()
        uri = f"sip:{to_number}@{self.server_host}"
        
        headers = [
            f"INVITE {uri} SIP/2.0",
            f"Via: SIP/2.0/UDP {local_ip}:{self.local_port};branch={self.branch}",
            "Max-Forwards: 70",
            f"From: <sip:{self.username}@{self.server_host}>;tag={self.tag}",
            f"To: <sip:{to_number}@{self.server_host}>",
            f"Contact: <sip:{self.username}@{local_ip}:{self.local_port}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} INVITE",
            "Content-Type: application/sdp",
        ]
        
        # Add authentication header if auth_info provided
        if auth_info:
            response, nc, cnonce = self.calculate_digest_response(auth_info, "INVITE", uri)
            auth_header = f'Digest username="{self.username}", realm="{auth_info.get("realm", "")}", '
            auth_header += f'nonce="{auth_info.get("nonce", "")}", uri="{uri}", '
            auth_header += f'response="{response}"'
            
            if auth_info.get('opaque'):
                auth_header += f', opaque="{auth_info["opaque"]}"'
            if auth_info.get('qop') and nc and cnonce:
                auth_header += f', qop={auth_info["qop"]}, nc={nc}, cnonce="{cnonce}"'
            
            headers.insert(-1, f"Authorization: {auth_header}")
        
        headers.append("Content-Length: 0")
        headers.append("")  # Empty line before body
        
        message = "\r\n".join(headers)
        return message.encode()

    def make_authenticated_call(self, to_number):
        """Make a SIP call with authentication"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', self.local_port))
            sock.settimeout(10)
            
            print(f"Making authenticated call from {self.username} to {to_number}")
            print(f"Using server: {self.server_host}:{self.server_port}")
            
            # First attempt without authentication
            invite_msg = self.create_invite_with_auth(to_number)
            print("Sending initial INVITE...")
            sock.sendto(invite_msg, (self.server_host, self.server_port))
            
            try:
                response, addr = sock.recvfrom(4096)
                response_text = response.decode()
                print(f"Received response from {addr}:")
                print(response_text)
                
                if "401 Unauthorized" in response_text or "407 Proxy Authentication Required" in response_text:
                    print("Authentication required, sending authenticated request...")
                    
                    # Parse authentication challenge
                    auth_header = ""
                    for line in response_text.split('\r\n'):
                        if line.startswith('WWW-Authenticate:') or line.startswith('Proxy-Authenticate:'):
                            auth_header = line.split(':', 1)[1].strip()
                            break
                    
                    if auth_header:
                        auth_info = self.parse_auth_header(auth_header)
                        print(f"Auth info: {auth_info}")
                        
                        # Send authenticated request
                        self.cseq += 1
                        self.branch = f"z9hG4bK{random.randint(1000000, 9999999)}"
                        
                        auth_invite = self.create_invite_with_auth(to_number, auth_info)
                        print("Sending authenticated INVITE...")
                        sock.sendto(auth_invite, (self.server_host, self.server_port))
                        
                        # Wait for final response
                        response2, addr2 = sock.recvfrom(4096)
                        response2_text = response2.decode()
                        print(f"Final response from {addr2}:")
                        print(response2_text)
                        
                        if "200 OK" in response2_text:
                            print("Call connected successfully!")
                            time.sleep(5)  # Simulate call duration
                            print("Call ended")
                            return True
                        elif "100 Trying" in response2_text or "180 Ringing" in response2_text:
                            print("Call in progress...")
                            # Wait for more responses
                            while True:
                                try:
                                    resp, _ = sock.recvfrom(4096)
                                    resp_text = resp.decode()
                                    print("Progress response:")
                                    print(resp_text)
                                    if "200 OK" in resp_text:
                                        print("Call connected!")
                                        return True
                                    elif "486 Busy" in resp_text or "404 Not Found" in resp_text:
                                        print("Call failed")
                                        return False
                                except socket.timeout:
                                    print("Call timeout")
                                    break
                        else:
                            print("Authentication failed or call rejected")
                            return False
                elif "200 OK" in response_text:
                    print("Call connected without authentication!")
                    return True
                else:
                    print("Call failed")
                    return False
                    
            except socket.timeout:
                print("No response received - timeout")
                return False
                
        except Exception as e:
            print(f"Error making call: {e}")
            return False
        finally:
            sock.close()

def main():
    """Test the authenticated SIP client"""
    client = AuthenticatedSIPClient(
        server_host='192.168.1.187',
        server_port=5060,
        username='1001',
        password='tt55oo77'
    )
    
    # Make a call to the number
    success = client.make_authenticated_call('0796026659')
    
    if success:
        print("Call completed successfully!")
    else:
        print("Call failed!")

if __name__ == "__main__":
    main()
