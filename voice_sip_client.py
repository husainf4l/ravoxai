#!/usr/bin/env python3
"""
Voice-enabled SIP client with ElevenLabs integration
"""
import socket
import time
import random
import hashlib
import re
import os
import io
import threading
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from pydub import AudioSegment
from pydub.playback import play
import pygame

# Load environment variables
load_dotenv()

class VoiceSIPClient:
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
        
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()
        
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
            
            # Try different ElevenLabs API methods
            try:
                # Method 1: Direct generate method
                audio = self.elevenlabs_client.generate(
                    text=text,
                    voice=self.voice_id,
                    model="eleven_monolingual_v1"
                )
                
                # Save audio to file
                with open(filename, "wb") as audio_file:
                    for chunk in audio:
                        if chunk:
                            audio_file.write(chunk)
                            
            except Exception as e1:
                print(f"Method 1 failed: {e1}")
                try:
                    # Method 2: Text-to-speech convert
                    audio = self.elevenlabs_client.text_to_speech.convert(
                        voice_id=self.voice_id,
                        text=text,
                        model_id="eleven_monolingual_v1"
                    )
                    
                    with open(filename, "wb") as audio_file:
                        for chunk in audio:
                            if chunk:
                                audio_file.write(chunk)
                                
                except Exception as e2:
                    print(f"Method 2 failed: {e2}")
                    # Method 3: Basic requests approach
                    import requests
                    
                    url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
                    headers = {
                        "Accept": "audio/mpeg",
                        "Content-Type": "application/json",
                        "xi-api-key": self.elevenlabs_api_key
                    }
                    data = {
                        "text": text,
                        "model_id": "eleven_monolingual_v1",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": 0.5
                        }
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

    def play_audio_file(self, filename):
        """Play audio file using pygame with format conversion"""
        try:
            print(f"Playing audio file: {filename}")
            
            # Convert audio to proper format using pydub
            try:
                audio = AudioSegment.from_file(filename)
                # Convert to WAV format with proper parameters
                wav_filename = filename.replace('.wav', '_converted.wav')
                audio.export(wav_filename, format="wav", 
                           parameters=["-acodec", "pcm_s16le", "-ar", "44100", "-ac", "1"])
                
                # Load and play the converted file
                pygame.mixer.music.load(wav_filename)
                pygame.mixer.music.play()
                
                # Wait for playback to complete
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                
                # Clean up converted file
                if os.path.exists(wav_filename):
                    os.remove(wav_filename)
                    
                print("Audio playback completed")
                return True
                
            except Exception as conversion_error:
                print(f"Audio conversion failed: {conversion_error}")
                # Try playing original file directly
                try:
                    pygame.mixer.music.load(filename)
                    pygame.mixer.music.play()
                    
                    while pygame.mixer.music.get_busy():
                        time.sleep(0.1)
                    
                    print("Direct audio playback completed")
                    return True
                except Exception as direct_error:
                    print(f"Direct playback also failed: {direct_error}")
                    return False
                    
        except Exception as e:
            print(f"Error playing audio: {e}")
            return False

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

    def make_voice_call(self, to_number, message_text="Hello! This is a test call from your VoIP agent. Can you hear me clearly?"):
        """Make a SIP call and play generated voice message"""
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
            sock.settimeout(15)
            
            print(f"Making voice call from {self.username} to {to_number}")
            print(f"Using server: {self.server_host}:{self.server_port}")
            
            # First attempt without authentication
            invite_msg = self.create_invite_with_auth(to_number)
            print("Sending initial INVITE...")
            sock.sendto(invite_msg, (self.server_host, self.server_port))
            
            try:
                response, addr = sock.recvfrom(4096)
                response_text = response.decode()
                print(f"Received response from {addr}:")
                print(response_text[:200] + "..." if len(response_text) > 200 else response_text)
                
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
                        
                        # Send authenticated request
                        self.cseq += 1
                        self.branch = f"z9hG4bK{random.randint(1000000, 9999999)}"
                        
                        auth_invite = self.create_invite_with_auth(to_number, auth_info)
                        print("Sending authenticated INVITE...")
                        sock.sendto(auth_invite, (self.server_host, self.server_port))
                        
                        # Wait for final response
                        response2, addr2 = sock.recvfrom(4096)
                        response2_text = response2.decode()
                        print(f"Final response: {response2_text[:100]}...")
                        
                        if "200 OK" in response2_text:
                            print("Call connected successfully!")
                            print("Playing generated voice message...")
                            self.play_audio_file(audio_file)
                            print("Voice message played")
                            return True
                        elif "100 Trying" in response2_text or "180 Ringing" in response2_text or "183 Session Progress" in response2_text:
                            print("Call in progress...")
                            # Wait for call to be answered
                            while True:
                                try:
                                    resp, _ = sock.recvfrom(4096)
                                    resp_text = resp.decode()
                                    print(f"Progress: {resp_text.split()[1:3]}")
                                    
                                    if "200 OK" in resp_text:
                                        print("Call answered! Playing voice message...")
                                        time.sleep(1)  # Give time for call to stabilize
                                        self.play_audio_file(audio_file)
                                        print("Voice message completed")
                                        time.sleep(2)  # Keep call active briefly
                                        return True
                                    elif "486 Busy" in resp_text or "404 Not Found" in resp_text:
                                        print("Call failed - number busy or not found")
                                        return False
                                    elif "603 Decline" in resp_text:
                                        print("Call declined")
                                        return False
                                except socket.timeout:
                                    print("Call timeout")
                                    break
                        else:
                            print("Authentication failed or call rejected")
                            return False
                elif "200 OK" in response_text:
                    print("Call connected without authentication!")
                    self.play_audio_file(audio_file)
                    return True
                else:
                    print("Call failed")
                    return False
                    
            except socket.timeout:
                print("No response received - timeout")
                return False
                
        except Exception as e:
            print(f"Error making voice call: {e}")
            return False
        finally:
            if sock:
                sock.close()
            # Clean up temporary audio file
            if audio_file and os.path.exists(audio_file):
                os.remove(audio_file)

def main():
    """Test the voice-enabled SIP client"""
    print("Voice-enabled SIP Client Test")
    print("=============================")
    
    # Check if ElevenLabs API key is configured
    if not os.getenv('ELEVENLABS_API_KEY'):
        print("Please add your ELEVENLABS_API_KEY to the .env file")
        return
    
    client = VoiceSIPClient()
    
    # Test message
    test_message = "Hello! This is a test call from your VoIP agent. If you can hear this message clearly, the voice integration is working perfectly. Thank you for testing!"
    
    # Make a voice call
    print(f"Making voice call to 0796026659...")
    success = client.make_voice_call('0796026659', test_message)
    
    if success:
        print("Voice call completed successfully!")
    else:
        print("Voice call failed!")

if __name__ == "__main__":
    main()
