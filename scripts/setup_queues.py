#!/usr/bin/env python3

import boto3
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import get_config

def create_queue_if_not_exists(sqs_client, queue_name, queue_url):
    """Create SQS queue if it doesn't exist"""
    try:
        # Try to get queue attributes to check if it exists
        sqs_client.get_queue_attributes(QueueUrl=queue_url)
        print(f"✅ Queue '{queue_name}' already exists: {queue_url}")
        return True
    except sqs_client.exceptions.QueueDoesNotExist:
        print(f"❌ Queue '{queue_name}' does not exist")
        return False
    except Exception as e:
        print(f"❌ Error checking queue '{queue_name}': {e}")
        return False

def create_queue(sqs_client, queue_name):
    """Create a new SQS queue"""
    try:
        response = sqs_client.create_queue(
            QueueName=queue_name,
            Attributes={
                'VisibilityTimeout': '300',
                'MessageRetentionPeriod': '1209600',  # 14 days
                'ReceiveMessageWaitTimeSeconds': '20'
            }
        )
        queue_url = response['QueueUrl']
        print(f"✅ Created queue '{queue_name}': {queue_url}")
        return queue_url
    except Exception as e:
        print(f"❌ Error creating queue '{queue_name}': {e}")
        return None

def main():
    print("🔧 Setting up SQS Queues...")
    
    try:
        config = get_config()
        
        # Initialize SQS client
        sqs_client = boto3.client(
            'sqs',
            region_name=config.aws.region,
            aws_access_key_id=config.aws.access_key_id,
            aws_secret_access_key=config.aws.secret_access_key
        )
        
        # Queue configurations
        queues = [
            {
                'name': 'kontext-process-queue',
                'url': config.sqs.process_queue_url
            },
            {
                'name': 'kontext-processing-queue', 
                'url': config.sqs.processing_queue_url
            }
        ]
        
        print("\n📋 Checking existing queues...")
        for queue in queues:
            exists = create_queue_if_not_exists(sqs_client, queue['name'], queue['url'])
            
            if not exists:
                print(f"\n🔨 Creating queue '{queue['name']}'...")
                new_url = create_queue(sqs_client, queue['name'])
                if new_url:
                    print(f"📝 Update your .env.dev file with the new URL:")
                    if 'process-queue' in queue['name']:
                        print(f"PROCESS_QUEUE_URL={new_url}")
                    else:
                        print(f"PROCESSING_QUEUE_URL={new_url}")
        
        print("\n✅ Queue setup complete!")
        
    except Exception as e:
        print(f"❌ Error in queue setup: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()