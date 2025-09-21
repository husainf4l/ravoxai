#!/usr/bin/env python3
"""
Test script for uploading recordings and transcripts to existing calls
Usage: python test_media_upload.py <call_id> <recording_file> [transcript_file]
"""

import requests
import sys
import os
import json
from pathlib import Path

def test_media_upload(call_id: str, recording_file: str = None, transcript_file: str = None):
    """Test uploading media files for a call"""

    base_url = "http://localhost:8000"

    print(f"🎵 Testing media upload for call: {call_id}")
    print(f"📁 Recording file: {recording_file}")
    print(f"📝 Transcript file: {transcript_file}")

    # First, check if the call exists
    try:
        response = requests.get(f"{base_url}/calls/{call_id}")
        if response.status_code == 404:
            print(f"❌ Call {call_id} not found")
            return False
        call_data = response.json()
        print(f"✅ Call found: {call_data.get('subject', 'N/A')}")
    except Exception as e:
        print(f"❌ Error checking call: {e}")
        return False

    # Upload recording if provided
    if recording_file and os.path.exists(recording_file):
        print(f"\n📤 Uploading recording: {recording_file}")
        try:
            with open(recording_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{base_url}/calls/{call_id}/upload-media",
                    files=files,
                    data={'file_type': 'recording'}
                )

            if response.status_code == 200:
                result = response.json()
                print("✅ Recording uploaded successfully!")
                print(f"🔗 URL: {result['url']}")
                print(f"🗝️ S3 Key: {result['s3_key']}")
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ Error uploading recording: {e}")

    # Upload transcript if provided
    if transcript_file and os.path.exists(transcript_file):
        print(f"\n📤 Uploading transcript: {transcript_file}")
        try:
            with open(transcript_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{base_url}/calls/{call_id}/upload-media",
                    files=files,
                    data={'file_type': 'transcript'}
                )

            if response.status_code == 200:
                result = response.json()
                print("✅ Transcript uploaded successfully!")
                print(f"🔗 URL: {result['url']}")
                print(f"🗝️ S3 Key: {result['s3_key']}")
            else:
                print(f"❌ Upload failed: {response.status_code}")
                print(response.text)

        except Exception as e:
            print(f"❌ Error uploading transcript: {e}")

    # Check final media status
    print("
📊 Final media status:"    try:
        response = requests.get(f"{base_url}/calls/{call_id}/media")
        if response.status_code == 200:
            media_data = response.json()
            print(f"🎵 Recording available: {media_data['recording_available']}")
            print(f"📝 Transcript available: {media_data['transcript_available']}")
            if media_data['recording_url']:
                print(f"🔗 Recording URL: {media_data['recording_url']}")
            if media_data['transcript_url']:
                print(f"🔗 Transcript URL: {media_data['transcript_url']}")
        else:
            print(f"❌ Error getting media status: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking media status: {e}")

    return True

def create_sample_files():
    """Create sample recording and transcript files for testing"""
    print("🎵 Creating sample media files for testing...")

    # Create a sample transcript
    transcript_content = """Sample Call Transcript
========================

AI Agent: Hello! This is a sample call recording for testing purposes.

Caller: Hi there! This is just a test conversation.

AI Agent: Great! I'm testing the recording and transcript functionality.

Caller: Perfect! This will help verify that the media upload system works correctly.

AI Agent: Thank you for participating in this test call.

[Call ended - Duration: 45 seconds]
"""

    with open("sample_transcript.txt", "w") as f:
        f.write(transcript_content)

    print("✅ Created sample_transcript.txt")

    # Note: For audio files, you would need actual audio content
    # For now, we'll just create a placeholder
    with open("sample_recording.mp3", "w") as f:
        f.write("# This is a placeholder for an MP3 recording file\n")
        f.write("# In a real scenario, this would be actual audio data\n")

    print("✅ Created sample_recording.mp3 (placeholder)")

    return "sample_recording.mp3", "sample_transcript.txt"

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_media_upload.py <call_id> [recording_file] [transcript_file]")
        print("\nExample:")
        print("  python test_media_upload.py abc123")
        print("  python test_media_upload.py abc123 recording.mp3 transcript.txt")
        print("\nTo create sample files:")
        print("  python test_media_upload.py --create-samples")
        sys.exit(1)

    if sys.argv[1] == "--create-samples":
        recording_file, transcript_file = create_sample_files()
        print(f"\n🎯 Now test with: python test_media_upload.py <call_id> {recording_file} {transcript_file}")
        sys.exit(0)

    call_id = sys.argv[1]
    recording_file = sys.argv[2] if len(sys.argv) > 2 else None
    transcript_file = sys.argv[3] if len(sys.argv) > 3 else None

    success = test_media_upload(call_id, recording_file, transcript_file)
    sys.exit(0 if success else 1)