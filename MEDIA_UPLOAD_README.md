# 🎵 Media Upload Features

This document explains the new media upload functionality for testing and managing call recordings and transcripts.

## 📋 New API Endpoints

### 1. Enhanced Media Information Endpoint
```
GET /calls/{call_id}/media
```

Returns comprehensive media information for a call:
- Recording availability and URLs
- Transcript availability and URLs
- Call metadata (duration, status, timestamps)
- S3 media files list
- Media summary statistics

### 2. Media Upload Endpoint
```
POST /calls/{call_id}/upload-media
```

Upload recording or transcript files for existing calls:
- Supports both local file upload and S3 key reference
- Updates call record with media URLs
- Handles both audio recordings and text transcripts

## 🧪 Testing Tools

### 1. Command Line Test Script
```bash
# Test with existing call
python test_media_upload.py <call_id>

# Upload specific files
python test_media_upload.py <call_id> recording.mp3 transcript.txt

# Create sample files for testing
python test_media_upload.py --create-samples
```

### 2. Web Interface
Open `test_media_upload.html` in your browser:
- Upload recordings and transcripts via web form
- Check media status for any call
- Direct links to play recordings and view transcripts

## 📤 Upload Methods

### Method 1: File Upload
```python
# Upload from local file
response = requests.post(
    f"http://localhost:8000/calls/{call_id}/upload-media",
    files={'file': open('recording.mp3', 'rb')},
    data={'file_type': 'recording'}
)
```

### Method 2: S3 Key Reference
```python
# Reference existing S3 file
response = requests.post(
    f"http://localhost:8000/calls/{call_id}/upload-media",
    data={
        'file_type': 'recording',
        's3_key': 'call-recordings/2025/09/21/abc123-audio.mp3'
    }
)
```

## 🎯 Usage Examples

### Check Media Status
```bash
curl http://localhost:8000/calls/abc123/media
```

### Upload Recording
```bash
curl -X POST \
  -F "file=@recording.mp3" \
  -F "file_type=recording" \
  http://localhost:8000/calls/abc123/upload-media
```

### Upload Transcript
```bash
curl -X POST \
  -F "file=@transcript.txt" \
  -F "file_type=transcript" \
  http://localhost:8000/calls/abc123/upload-media
```

## 📊 Media Status Response

```json
{
  "call_id": "abc123",
  "recording_available": true,
  "recording_url": "https://s3.amazonaws.com/...",
  "recording_s3_key": "call-recordings/2025/09/21/abc123-audio.mp3",
  "transcript_available": true,
  "transcript_url": "https://s3.amazonaws.com/...",
  "transcript_s3_key": "call-transcripts/2025/09/21/abc123-transcript.txt",
  "duration_seconds": 45,
  "recording_format": "mp3",
  "call_status": "completed",
  "call_start_time": "2025-09-21T10:30:00",
  "call_end_time": "2025-09-21T10:30:45",
  "s3_media_files": [...],
  "media_summary": {
    "total_files": 2,
    "has_audio": true,
    "has_transcript": true,
    "recording_formats": ["mp3"]
  }
}
```

## 🔗 Integration with Dashboard

The dashboard automatically detects and displays:
- **Recording Badge** 🟥 when audio is available
- **Transcript Badge** 🟩 when transcript exists
- **Direct Play/View Links** for immediate access
- **Real-time Status Updates** every 60 seconds

## 🚀 Quick Start

1. **Start the API server:**
   ```bash
   python main.py
   ```

2. **Open the web test interface:**
   ```bash
   open test_media_upload.html
   ```

3. **Or use the command line:**
   ```bash
   python test_media_upload.py --create-samples
   python test_media_upload.py <call_id> sample_recording.mp3 sample_transcript.txt
   ```

4. **Check the dashboard:**
   ```
   http://localhost:8000/dashboard
   ```

## 📁 File Structure

```
sip/
├── main.py                    # Enhanced with media endpoints
├── test_media_upload.py       # Command line test script
├── test_media_upload.html     # Web test interface
├── sample_recording.mp3       # Test recording file
└── sample_transcript.txt      # Test transcript file
```

## 🎵 Recording Format Support

- **Audio:** MP3, WAV, M4A
- **Transcripts:** TXT, JSON
- **Storage:** AWS S3 with public read access
- **URLs:** Direct links for streaming/playback

## 🔧 Configuration

Make sure your `.env` file has the correct S3 configuration:
```
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=your_bucket
AWS_REGION=me-central-1
```

The system will automatically handle media uploads and provide direct links for your dashboard! 🎉