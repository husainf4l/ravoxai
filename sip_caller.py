import sys
import time
from asterisk.ami import AMIClient

class AsteriskCaller:
    def __init__(self, host='192.168.1.187', port=5060, username='admin', password='tt55oo77'):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None

    def connect(self):
        try:
            self.client = AMIClient(address=self.host, port=self.port)
            self.client.login(username=self.username, secret=self.password)
            print(f"Connected to Asterisk at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"Failed to connect to Asterisk: {e}")
            return False

    def make_call(self, from_channel, to_number):
        """
        Make a call using Asterisk Manager Interface (AMI)
        from_channel: e.g., 'SIP/1001' 
        to_number: e.g., '0790002033'
        """
        try:
            action = {
                'Action': 'Originate',
                'Channel': from_channel,
                'Context': 'from-internal',
                'Exten': to_number,
                'Priority': '1',
                'CallerID': '1001',
                'Timeout': '30000'
            }
            
            future = self.client.send_action(action)
            response = future.response
            
            if response.response == 'Success':
                print(f"Call initiated successfully from {from_channel} to {to_number}")
                return True
            else:
                print(f"Failed to initiate call: {response}")
                return False
                
        except Exception as e:
            print(f"Error making call: {e}")
            return False

    def disconnect(self):
        if self.client:
            self.client.logoff()
            print("Disconnected from Asterisk")

def main():
    # Initialize Asterisk caller
    caller = AsteriskCaller(
        host='192.168.1.187',
        port=5060,
        username='admin',  # Replace with your AMI username
        password='tt55oo77'   # Replace with your AMI password
    )
    
    # Connect to Asterisk
    if not caller.connect():
        print("Failed to connect to Asterisk AMI")
        sys.exit(1)
    
    try:
        # Make a call from SIP/1001 to 0796026659
        success = caller.make_call('SIP/1001', '0796026659')
        
        if success:
            print("Call initiated. Waiting...")
            time.sleep(10)  # Wait for call to complete
        else:
            print("Call failed")
            
    finally:
        caller.disconnect()

if __name__ == "__main__":
    main()
