#!/usr/bin/env python3
"""
Test script for making calls to your phone number
Usage: python test_call.py [subject] [agent_name]
"""

import requests
import sys
import json

def test_call_to_your_number(subject: str = "Test call from AI system", agent_name: str = "AI Assistant"):
    """Make a test call to your phone number"""

    base_url = "http://localhost:8000"

    # Your phone number
    your_number = "0796026659"

    call_data = {
        "phone_number": your_number,
        "subject": subject,
        "agent_name": agent_name,
        "caller_name": "Husain",
        "company_name": "RavoX AI",
        "main_prompt": f"This is a test call to verify the AI calling system is working correctly. The subject is: {subject}. Please respond to confirm you received this call."
    }

    print(f"📞 Making test call to: {your_number}")
    print(f"📝 Subject: {subject}")
    print(f"🤖 Agent: {agent_name}")
    print(f"🏢 Company: RavoX AI")

    try:
        response = requests.post(f"{base_url}/make-call", json=call_data)

        if response.status_code == 200:
            result = response.json()
            print("✅ Call initiated successfully!")
            print(f"🆔 Call ID: {result.get('call_id', 'N/A')}")
            print(f"📊 Status: {result.get('status', 'N/A')}")

            if result.get('call_id'):
                print(f"\n🔍 You can check the call status at:")
                print(f"   http://localhost:8000/calls/{result['call_id']}")
                print(f"   http://localhost:8000/dashboard")

        else:
            print(f"❌ Call failed with status: {response.status_code}")
            print(f"Response: {response.text}")

    except Exception as e:
        print(f"❌ Error making call: {e}")

if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "Test call from AI system"
    agent_name = sys.argv[2] if len(sys.argv) > 2 else "AI Assistant"

    test_call_to_your_number(subject, agent_name)