"""
AWS S3 Media Storage Service
Handles uploading and managing call recordings and media files
"""

import boto3
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from botocore.exceptions import ClientError, NoCredentialsError
import mimetypes

load_dotenv()
logger = logging.getLogger(__name__)


class S3MediaService:
    """AWS S3 service for handling call recordings and media"""
    
    def __init__(self):
        """Initialize S3 client with credentials from environment"""
        self.aws_access_key = os.getenv('AWS_ACCESS_KEY_ID')
        self.aws_secret_key = os.getenv('AWS_SECRET_ACCESS_KEY')
        self.aws_region = os.getenv('AWS_REGION', 'me-central-1')
        self.bucket_name = os.getenv('AWS_BUCKET_NAME', '4wk-garage-media')
        
        if not all([self.aws_access_key, self.aws_secret_key, self.bucket_name]):
            raise ValueError("Missing required AWS credentials or bucket name in environment variables")
        
        # Initialize S3 client
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=self.aws_access_key,
            aws_secret_access_key=self.aws_secret_key,
            region_name=self.aws_region
        )
        
        logger.info(f"✅ S3 Media Service initialized - Region: {self.aws_region}, Bucket: {self.bucket_name}")
    
    def upload_recording(self, file_path: str, call_id: str, file_type: str = "audio") -> dict:
        """
        Upload call recording to S3
        
        Args:
            file_path: Local path to the recording file
            call_id: Unique call identifier
            file_type: Type of file (audio, video, transcript)
            
        Returns:
            dict: Upload result with S3 URL and metadata
        """
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Recording file not found: {file_path}")
            
            # Generate S3 key with organized structure
            timestamp = datetime.utcnow().strftime("%Y/%m/%d")
            file_extension = os.path.splitext(file_path)[1]
            s3_key = f"call-recordings/{timestamp}/{call_id}-{file_type}{file_extension}"
            
            # Determine content type
            content_type, _ = mimetypes.guess_type(file_path)
            if not content_type:
                content_type = 'application/octet-stream'
            
            # Upload file with metadata
            extra_args = {
                'ContentType': content_type,
                'Metadata': {
                    'call_id': call_id,
                    'file_type': file_type,
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'service': 'ai-call-service'
                }
            }
            
            logger.info(f"📤 Uploading recording to S3: {s3_key}")
            self.s3_client.upload_file(file_path, self.bucket_name, s3_key, ExtraArgs=extra_args)
            
            # Generate public URL (adjust based on your bucket policy)
            s3_url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            
            logger.info(f"✅ Recording uploaded successfully: {s3_url}")
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "bucket": self.bucket_name,
                "file_size": os.path.getsize(file_path),
                "content_type": content_type,
                "message": "Recording uploaded successfully"
            }
            
        except FileNotFoundError as e:
            logger.error(f"❌ File not found: {e}")
            return {"success": False, "error": str(e)}
        except NoCredentialsError:
            logger.error("❌ AWS credentials not found")
            return {"success": False, "error": "AWS credentials not configured"}
        except ClientError as e:
            logger.error(f"❌ AWS S3 error: {e}")
            return {"success": False, "error": f"S3 upload failed: {str(e)}"}
        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            return {"success": False, "error": f"Upload failed: {str(e)}"}
    
    def upload_transcript(self, transcript_content: str, call_id: str) -> dict:
        """
        Upload conversation transcript as text file to S3
        
        Args:
            transcript_content: Full conversation transcript
            call_id: Unique call identifier
            
        Returns:
            dict: Upload result with S3 URL
        """
        try:
            # Generate S3 key for transcript
            timestamp = datetime.utcnow().strftime("%Y/%m/%d")
            s3_key = f"call-transcripts/{timestamp}/{call_id}-transcript.txt"
            
            # Upload transcript as string
            extra_args = {
                'ContentType': 'text/plain',
                'Metadata': {
                    'call_id': call_id,
                    'file_type': 'transcript',
                    'upload_timestamp': datetime.utcnow().isoformat(),
                    'service': 'ai-call-service'
                }
            }
            
            logger.info(f"📤 Uploading transcript to S3: {s3_key}")
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=transcript_content.encode('utf-8'),
                **extra_args
            )
            
            s3_url = f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{s3_key}"
            logger.info(f"✅ Transcript uploaded successfully: {s3_url}")
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "bucket": self.bucket_name,
                "message": "Transcript uploaded successfully"
            }
            
        except Exception as e:
            logger.error(f"❌ Transcript upload failed: {e}")
            return {"success": False, "error": f"Transcript upload failed: {str(e)}"}
    
    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> str:
        """
        Generate presigned URL for secure access to recordings
        
        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            
        Returns:
            str: Presigned URL for secure access
        """
        try:
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None
    
    def delete_recording(self, s3_key: str) -> bool:
        """
        Delete recording from S3
        
        Args:
            s3_key: S3 object key to delete
            
        Returns:
            bool: Success status
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"🗑️ Deleted recording: {s3_key}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete recording: {e}")
            return False
    
    def list_call_recordings(self, call_id: str) -> list:
        """
        List all recordings for a specific call
        
        Args:
            call_id: Call identifier
            
        Returns:
            list: List of recording objects for the call
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=f"call-recordings/"
            )
            
            recordings = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if call_id in obj['Key']:
                        recordings.append({
                            'key': obj['Key'],
                            'size': obj['Size'],
                            'last_modified': obj['LastModified'],
                            'url': f"https://{self.bucket_name}.s3.{self.aws_region}.amazonaws.com/{obj['Key']}"
                        })
            
            return recordings
        except Exception as e:
            logger.error(f"❌ Failed to list recordings: {e}")
            return []


# Global instance
s3_service = None

def get_s3_service():
    """Get or create S3 service instance"""
    global s3_service
    if s3_service is None:
        try:
            s3_service = S3MediaService()
        except ValueError as e:
            logger.error(f"❌ S3 service initialization failed: {e}")
            s3_service = None
    return s3_service


def test_s3_connection():
    """Test S3 connection with actual upload capability (like the working code)"""
    try:
        service = get_s3_service()
        if not service:
            return False
        
        # Test with a minimal operation that matches your working code pattern
        # Try to get bucket location instead of listing (requires less permissions)
        try:
            service.s3_client.get_bucket_location(Bucket=service.bucket_name)
            logger.info("✅ S3 connection test successful")
            return True
        except Exception as bucket_error:
            # If get_bucket_location fails, try a minimal put_object test
            # This matches what your recording code actually does
            test_key = f"connection-test/{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.txt"
            try:
                service.s3_client.put_object(
                    Bucket=service.bucket_name,
                    Key=test_key,
                    Body=b'connection test',
                    ContentType='text/plain'
                )
                # Clean up the test file
                service.s3_client.delete_object(Bucket=service.bucket_name, Key=test_key)
                logger.info("✅ S3 connection test successful (via upload test)")
                return True
            except Exception as upload_error:
                logger.error(f"❌ S3 connection test failed: {upload_error}")
                return False
                
    except Exception as e:
        logger.error(f"❌ S3 connection test failed: {e}")
        return False