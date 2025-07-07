#!/usr/bin/env python3
"""
RTP-enabled SIP client that sends audio through the call
"""
import socket
import time
import random
import hashlib
import re
import os
import threading
import struct
import wave
import audioop
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment

# Load environment variables
load_dotenv()

class RTPAudioStreamer:
    """Simple RTP audio streamer for SIP calls"""
    
    def __init__(self, remote_ip, remote_port, local_port=None):
        self.remote_ip = remote_ip
        self.remote_port = remote_port
        self.local_port = local_port or random.randint(10000, 20000)
        self.socket = None
        self.sequence_number = random.randint(0, 65535)
        self.timestamp = random.randint(0, 4294967295)
        self.ssrc = random.randint(0, 4294967295)
        
    def create_rtp_packet(self, payload):
        """Create RTP packet with G.711 u-law payload"""
        # RTP Header (12 bytes)
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 0  # G.711 u-law
        
        # Pack RTP header
        header = struct.pack('!BBHII',
            (version << 6) | (padding << 5) | (extension << 4) | cc,
            (marker << 7) | pt,
            self.sequence_number,
            self.timestamp,
            self.ssrc
        )
        
        self.sequence_number = (self.sequence_number + 1) % 65536
        self.timestamp += len(payload)
        
        return header + payload
    
    def convert_to_ulaw(self, audio_data):
        """Convert audio to G.711 u-law format with proper encoding"""
        try:
            # Use Python's built-in audioop for proper u-law conversion
            # audioop expects 16-bit linear PCM data
            ulaw_data = audioop.lin2ulaw(audio_data, 2)  # 2 = 16-bit samples
            return ulaw_data
        except Exception as e:
            print(f"U-law conversion error: {e}")
            # Fallback: Simple linear-to-ulaw conversion
            ulaw_data = bytearray()
            for i in range(0, len(audio_data), 2):
                if i + 1 < len(audio_data):
                    # Convert 16-bit sample to u-law
                    sample = struct.unpack('<h', audio_data[i:i+2])[0]
                    # Apply u-law compression algorithm
                    if sample >= 0:
                        sign = 0x80
                        magnitude = sample
                    else:
                        sign = 0x00
                        magnitude = -sample
                    
                    # Clip magnitude to 12 bits
                    magnitude = min(magnitude, 0x1FFF)
                    
                    # Find segment
                    segment = 0
                    temp = magnitude >> 5
                    while temp and segment < 7:
                        segment += 1
                        temp >>= 1
                    
                    # Build u-law byte
                    ulaw_byte = sign | (segment << 4) | ((magnitude >> (segment + 1)) & 0x0F)
                    ulaw_data.append(ulaw_byte ^ 0xFF)  # Complement for transmission
            
            return bytes(ulaw_data)
    
    def stream_audio_file(self, audio_file_path):
        """Stream audio file as RTP packets"""
        try:
            # Create UDP socket for RTP
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.bind(('', self.local_port))
            
            print(f"Streaming audio to {self.remote_ip}:{self.remote_port}")
            
            # Load and convert audio file
            audio = AudioSegment.from_file(audio_file_path)
            # Convert to 8kHz, mono, 16-bit (standard for G.711)
            audio = audio.set_frame_rate(8000).set_channels(1)
            
            # Get raw audio data
            raw_audio = audio.raw_data
            
            # Convert to u-law
            ulaw_audio = self.convert_to_ulaw(raw_audio)
            
            # Send in chunks (160 bytes = 20ms of audio at 8kHz)
            chunk_size = 160
            for i in range(0, len(ulaw_audio), chunk_size):
                chunk = ulaw_audio[i:i+chunk_size]
                if len(chunk) < chunk_size:
                    # Pad last chunk with silence
                    chunk += b'\x7f' * (chunk_size - len(chunk))
                
                # Create and send RTP packet
                rtp_packet = self.create_rtp_packet(chunk)
                self.socket.sendto(rtp_packet, (self.remote_ip, self.remote_port))
                
                # Wait 20ms between packets (50 packets per second)
                time.sleep(0.02)
            
            print("Audio streaming completed")
            return True
            
        except Exception as e:
            print(f"Error streaming audio: {e}")
            return False
        finally:
            if self.socket:
                self.socket.close()

class VoiceRTPSIPClient:
    def __init__(self, server_host=None, server_port=5060, username=None, password=None):
        # Load from .env if not provided
        self.server_host = server_host or os.getenv('SIP_SERVER', '192.168.1.187')
        self.server_port = server_port or int(os.getenv('SIP_PORT', '5060'))
        self.username = username or os.getenv('SIP_USERNAME', '1001')
        self.password = password or os.getenv('SIP_PASSWORD', 'tt55oo77')
        
        # ElevenLabs configuration
        self.elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
        self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', '21m00Tcm4TlvDq8ikWAM').strip()
        
        # SIP connection details
        self.local_port = random.randint(5060, 6000)
        self.rtp_port = random.randint(10000, 20000)
        self.call_id = f"{random.randint(1000000, 9999999)}@{socket.gethostname()}"
        self.tag = f"tag{random.randint(1000, 9999)}"
        self.branch = f"z9hG4bK{random.randint(1000000, 9999999)}"
        self.cseq = 1
        
        # Initialize ElevenLabs client
        if self.elevenlabs_api_key:
            self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        else:
            print("Warning: ELEVENLABS_API_KEY not found in .env file")
            self.elevenlabs_client = None
    
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

    def generate_speech(self, text, filename="temp_speech.wav"):
        """Generate speech using ElevenLabs API"""
        if not self.elevenlabs_client:
            print("ElevenLabs client not initialized")
            return None
            
        try:
            print(f"Generating speech for: '{text}'")
            
            # Generate audio using ElevenLabs
            try:
                # Method 1: Using text_to_speech.convert
                audio = self.elevenlabs_client.text_to_speech.convert(
                    voice_id=self.voice_id,
                    text=text,
                    model_id="eleven_monolingual_v1"
                )
                
                with open(filename, "wb") as audio_file:
                    for chunk in audio:
                        if chunk:
                            audio_file.write(chunk)
                            
            except Exception as e1:
                print(f"Method 1 failed: {e1}")
                # Method 2: Basic requests approach
                import requests
                
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": self.elevenlabs_api_key
                }
                data = {
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",  # Latest high-quality model
                    "voice_settings": {
                        "stability": 0.75,
                        "similarity_boost": 0.85,
                        "style": 0.2,
                        "use_speaker_boost": True
                    },
                    "output_format": "mp3_22050_32"  # Optimized for voice calls
                }
                
                response = requests.post(url, json=data, headers=headers)
                
                if response.status_code == 200:
                    with open(filename, "wb") as audio_file:
                        audio_file.write(response.content)
                else:
                    print(f"API request failed: {response.status_code} - {response.text}")
                    return None
            
            print(f"Speech generated and saved to {filename}")
            return filename
            
        except Exception as e:
            print(f"Error generating speech: {e}")
            return None

    def create_sdp_body(self, local_ip):
        """Create SDP body with μ-law and A-law codec support"""
        session_id = random.randint(1000000, 9999999)
        version = random.randint(1000000, 9999999)
        
        sdp = f"""v=0
o=- {session_id} {version} IN IP4 {local_ip}
s=-
c=IN IP4 {local_ip}
t=0 0
m=audio {self.rtp_port} RTP/AVP 0 8
a=rtpmap:0 PCMU/8000
a=rtpmap:8 PCMA/8000
a=sendrecv
a=ptime:20
"""
        return sdp

    def parse_auth_header(self, auth_header):
        """Parse WWW-Authenticate header"""
        auth_info = {}
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

    def create_invite_with_auth_and_sdp(self, to_number, auth_info=None):
        """Create SIP INVITE message with SDP body"""
        local_ip = self.get_local_ip()
        uri = f"sip:{to_number}@{self.server_host}"
        
        # Create SDP body
        sdp_body = self.create_sdp_body(local_ip)
        
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
        
        headers.append(f"Content-Length: {len(sdp_body)}")
        headers.append("")  # Empty line before body
        headers.append(sdp_body)
        
        message = "\r\n".join(headers)
        return message.encode()

    def parse_sdp_response(self, response_text):
        """Parse SDP from 200 OK response to get remote RTP details"""
        try:
            # Extract SDP body
            sdp_start = response_text.find('\r\n\r\n')
            if sdp_start == -1:
                return None, None
            
            sdp_body = response_text[sdp_start + 4:]
            
            remote_ip = None
            remote_port = None
            
            for line in sdp_body.split('\r\n'):
                if line.startswith('c=IN IP4 '):
                    remote_ip = line.split(' ')[2]
                elif line.startswith('m=audio '):
                    parts = line.split(' ')
                    if len(parts) >= 2:
                        remote_port = int(parts[1])
            
            return remote_ip, remote_port
        except Exception as e:
            print(f"Error parsing SDP: {e}")
            return None, None

    def make_voice_call_with_rtp(self, to_number, message_text="Hello! This is a test call from your VoIP agent with RTP audio streaming."):
        """Make a SIP call and stream generated voice through RTP"""
        sock = None
        audio_file = None
        
        try:
            # Generate speech first
            print("Generating speech...")
            audio_file = self.generate_speech(message_text)
            if not audio_file:
                print("Failed to generate speech")
                return False
            
            # Create socket for SIP call
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(('', self.local_port))
            sock.settimeout(30)  # Increased timeout to 30 seconds
            
            print(f"Making RTP voice call from {self.username} to {to_number}")
            print(f"SIP server: {self.server_host}:{self.server_port}")
            print(f"Local RTP port: {self.rtp_port}")
            
            # First attempt without authentication
            invite_msg = self.create_invite_with_auth_and_sdp(to_number)
            print("Sending INVITE with SDP...")
            sock.sendto(invite_msg, (self.server_host, self.server_port))
            
            response, addr = sock.recvfrom(4096)
            response_text = response.decode()
            print(f"Received response from {addr}:")
            print(response_text[:200] + "..." if len(response_text) > 200 else response_text)
            
            if "401 Unauthorized" in response_text:
                print("Authentication required...")
                
                # Parse authentication challenge
                auth_header = ""
                for line in response_text.split('\r\n'):
                    if line.startswith('WWW-Authenticate:'):
                        auth_header = line.split(':', 1)[1].strip()
                        break
                
                if auth_header:
                    auth_info = self.parse_auth_header(auth_header)
                    
                    # Send authenticated request
                    self.cseq += 1
                    self.branch = f"z9hG4bK{random.randint(1000000, 9999999)}"
                    
                    auth_invite = self.create_invite_with_auth_and_sdp(to_number, auth_info)
                    print("Sending authenticated INVITE with SDP...")
                    sock.sendto(auth_invite, (self.server_host, self.server_port))
                    
                    # Wait for responses
                    call_answered = False
                    start_time = time.time()
                    max_wait_time = 45  # Maximum wait time for call to be answered
                    
                    while time.time() - start_time < max_wait_time:
                        try:
                            resp, _ = sock.recvfrom(4096)
                            resp_text = resp.decode()
                            status_code = resp_text.split()[1] if len(resp_text.split()) > 1 else 'Unknown'
                            print(f"Response: {status_code}")
                            
                            if "100 Trying" in resp_text:
                                print("Call is being processed...")
                            elif "180 Ringing" in resp_text:
                                print("Phone is ringing...")
                            elif "183 Session Progress" in resp_text:
                                print("Session in progress...")
                            elif "200 OK" in resp_text:
                                print("Call answered! Parsing remote RTP details...")
                                call_answered = True
                                
                                # Parse SDP to get remote RTP endpoint
                                remote_ip, remote_port = self.parse_sdp_response(resp_text)
                                
                                if remote_ip and remote_port:
                                    print(f"Remote RTP: {remote_ip}:{remote_port}")
                                    
                                    # Send ACK
                                    ack_msg = self.create_ack_message(to_number)
                                    sock.sendto(ack_msg, (self.server_host, self.server_port))
                                    
                                    # Start RTP audio streaming
                                    print("Starting RTP audio stream...")
                                    rtp_streamer = RTPAudioStreamer(remote_ip, remote_port, self.rtp_port)
                                    
                                    # Stream audio in a separate thread
                                    def stream_audio():
                                        time.sleep(1)  # Give time for call to stabilize
                                        rtp_streamer.stream_audio_file(audio_file)
                                    
                                    audio_thread = threading.Thread(target=stream_audio)
                                    audio_thread.start()
                                    audio_thread.join()
                                    
                                    print("RTP audio streaming completed")
                                    time.sleep(2)  # Keep call active briefly
                                    return True
                                else:
                                    print("Could not parse remote RTP details")
                                    return False
                            elif "486 Busy" in resp_text or "404 Not Found" in resp_text:
                                print("Call failed - number busy or not found")
                                return False
                            elif "603 Decline" in resp_text:
                                print("Call declined by recipient")
                                return False
                            elif "408 Request Timeout" in resp_text:
                                print("Call request timed out")
                                return False
                                
                        except socket.timeout:
                            # Check if we're still within the maximum wait time
                            if time.time() - start_time >= max_wait_time:
                                print("Maximum wait time exceeded - call not answered")
                                break
                            else:
                                print("Waiting for call to be answered...")
                                continue
                    
                    if not call_answered:
                        print("Call was not answered within the timeout period")
                        return False
            
            return False
                
        except Exception as e:
            print(f"Error making RTP voice call: {e}")
            return False
        finally:
            if sock:
                sock.close()
            # Clean up temporary audio file
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)

    def create_ack_message(self, to_number):
        """Create ACK message to complete call setup"""
        local_ip = self.get_local_ip()
        uri = f"sip:{to_number}@{self.server_host}"
        
        headers = [
            f"ACK {uri} SIP/2.0",
            f"Via: SIP/2.0/UDP {local_ip}:{self.local_port};branch={self.branch}",
            f"From: <sip:{self.username}@{self.server_host}>;tag={self.tag}",
            f"To: <sip:{to_number}@{self.server_host}>",
            f"Call-ID: {self.call_id}",
            f"CSeq: {self.cseq} ACK",
            "Content-Length: 0",
            ""
        ]
        
        message = "\r\n".join(headers)
        return message.encode()

def main():
    """Test the RTP voice-enabled SIP client"""
    print("RTP Voice-enabled SIP Client Test")
    print("==================================")
    
    # Check if ElevenLabs API key is configured
    if not os.getenv('ELEVENLABS_API_KEY'):
        print("Please add your ELEVENLABS_API_KEY to the .env file")
        return
    
    client = VoiceRTPSIPClient()
    
    # Test message
    test_message = "Hello! This is a test call with RTP audio streaming. If you can hear this message on your phone, the voice integration is working perfectly through the SIP call. Thank you for testing!"
    
    # Make a voice call with RTP streaming
    print(f"Making RTP voice call to 0796026659...")
    success = client.make_voice_call_with_rtp('0796026659', test_message)
    
    if success:
        print("RTP voice call completed successfully!")
    else:
        print("RTP voice call failed!")

if __name__ == "__main__":
    main()
