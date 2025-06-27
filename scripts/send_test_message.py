#!/usr/bin/env python3

import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import get_config
from src.repositories.sqs_repository import SQSRepository
from src.models.messages import ProcessRequestMessage, ContentType

def send_test_message():
    """Send a test message to the process queue"""
    print("📤 Sending test message...")
    
    try:
        config = get_config()
        sqs_repository = SQSRepository(config)
        
        # Create test message
        test_message = ProcessRequestMessage(
            content_id=str(uuid.uuid4()),
            content_type=ContentType.DOCUMENT,
            file_name="test-document.pdf",
            s3_key="test/test-document.pdf",
            s3_bucket="kontext-dev-bucket",
            mime_type="application/pdf",
            file_size=1024567,
            project_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Send message
        success = sqs_repository.send_message(
            queue_url=config.sqs.process_queue_url,
            message=test_message
        )
        
        if success:
            print("✅ Test message sent successfully!")
            print(f"Content ID: {test_message.content_id}")
            print(f"File Name: {test_message.file_name}")
        else:
            print("❌ Failed to send test message")
            
    except Exception as e:
        print(f"❌ Error sending test message: {e}")

if __name__ == "__main__":
    send_test_message()