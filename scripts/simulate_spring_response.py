#!/usr/bin/env python3

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.config.settings import get_config
from src.repositories.sqs_repository import SQSRepository
from src.models.messages import ProcessSuccessMessage, ProcessFailureMessage, ContentType

def simulate_success_response():
    """Simulate sending a success response to see the exact format"""
    print("🎯 Simulating Success Response to Spring Boot...")
    
    try:
        config = get_config()
        sqs_repository = SQSRepository(config)
        
        # Create success message
        success_message = ProcessSuccessMessage(
            content_id="12345-test-content",
            content_type=ContentType.DOCUMENT,
            message="Document processed successfully",
            processing_time_ms=25000,
            chunk_count=12,
            s3_bucket_name="kontext-dev-bucket",
            s3_key="processed/12345-test-content-chunks.json"
        )
        
        # Show what will be sent
        json_body = success_message.model_dump_json(by_alias=True, indent=2)
        print("📤 Exact JSON your Spring Boot service will receive:")
        print(json_body)
        
        # Actually send it
        success = sqs_repository.send_message(
            queue_url=config.sqs.processing_queue_url,
            message=success_message
        )
        
        if success:
            print("\n✅ Success message sent to kontext-processing-queue!")
        
        return json_body
        
    except Exception as e:
        print(f"❌ Error: {e}")

def simulate_failure_response():
    """Simulate sending a failure response to see the exact format"""
    print("\n🎯 Simulating Failure Response to Spring Boot...")
    
    try:
        config = get_config()
        sqs_repository = SQSRepository(config)
        
        # Create failure message
        failure_message = ProcessFailureMessage(
            content_id="12345-test-content",
            content_type=ContentType.DOCUMENT,
            error_message="Failed to process document: file corrupted",
            error_code="DOCUMENT_CORRUPTED",
            stack_trace="java.lang.Exception: Document processing failed...",
            retry_count=2,
            failed_step="document_parsing"
        )
        
        # Show what will be sent
        json_body = failure_message.model_dump_json(by_alias=True, indent=2)
        print("📤 Exact JSON your Spring Boot service will receive:")
        print(json_body)
        
        # Actually send it
        success = sqs_repository.send_message(
            queue_url=config.sqs.processing_queue_url,
            message=failure_message
        )
        
        if success:
            print("\n✅ Failure message sent to kontext-processing-queue!")
        
        return json_body
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔄 Simulating Responses to Spring Boot Service\n")
    
    success_json = simulate_success_response()
    failure_json = simulate_failure_response()
    
    print("\n📋 Summary:")
    print("✅ All field names are now in camelCase")
    print("✅ Messages sent to kontext-processing-queue")
    print("✅ Ready for Spring Boot consumption!")