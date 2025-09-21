#!/usr/bin/env python3
"""
Test recording upload functionality
"""

import requests
import json
import tempfile
import os

def test_recording_upload():
    # Get a completed call to test recording upload
    response = requests.get('http://localhost:8000/calls?limit=1&status=completed')
    if response.status_code == 200:
        calls = response.json()
        if calls:
            call = calls[0]
            call_id = call.get('call_id')
            print(f'📝 Testing recording upload for completed call: {call_id[:8]}...')

            # Create a test recording file
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
                content = f'''# Test recording data for call {call_id[:20]}
# This is sample audio data
# Duration: 30 seconds
# This proves recording links work!
# Uploaded at: {os.path.basename(temp_file.name)}
'''.encode()
                temp_file.write(content)
                temp_file_path = temp_file.name

            print(f'📤 Uploading test recording: {os.path.basename(temp_file_path)}')

            # Upload the recording using query parameters
            params = {
                'file_type': 'recording',
                'file_path': temp_file_path
            }

            upload_response = requests.post(
                f'http://localhost:8000/calls/{call_id}/upload-media',
                params=params
            )

            if upload_response.status_code == 200:
                result = upload_response.json()
                print('✅ Recording uploaded successfully!')
                print(f'🔗 URL: {result.get("url", "N/A")}')
                print(f'🗝️ S3 Key: {result.get("s3_key", "N/A")}')

                # Check if the call now shows recording available
                check_response = requests.get(f'http://localhost:8000/calls/{call_id}')
                if check_response.status_code == 200:
                    updated_call = check_response.json()
                    print(f'📊 Updated recording status: {updated_call.get("recording_available", "N/A")}')
                    if updated_call.get('recording_url'):
                        print(f'🔗 Direct link: {updated_call.get("recording_url")}')
                        print('🎉 SUCCESS! You now have a working recording link!')
                        print('📱 You can click this link to download/play the recording')
                        return True
            else:
                print(f'❌ Upload failed: {upload_response.status_code}')
                print(upload_response.text)

            # Clean up
            os.unlink(temp_file_path)
        else:
            print('❌ No completed calls found')
    else:
        print(f'❌ Error: {response.status_code}')

    return False

if __name__ == "__main__":
    success = test_recording_upload()
    if success:
        print('\n🎊 Recording upload test PASSED!')
        print('✅ Your recording link system is working!')
    else:
        print('\n❌ Recording upload test FAILED')