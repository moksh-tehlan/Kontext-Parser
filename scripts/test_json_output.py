#!/usr/bin/env python3

import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.models.messages import ProcessSuccessMessage, ProcessFailureMessage, ContentType

def test_success_message_format():
    """Test the JSON output format for success messages"""
    print("🧪 Testing Success Message JSON Format...")
    
    success_message = ProcessSuccessMessage(
        content_id="test-content-id",
        content_type=ContentType.DOCUMENT,
        message="Document processed successfully",
        processing_time_ms=30000,
        chunk_count=15,
        s3_bucket_name="kontext-dev-bucket",
        s3_key="processed/test-content-id-chunks.json"
    )
    
    # Test with by_alias=True (what we send to Spring Boot)
    json_output = success_message.model_dump_json(by_alias=True, indent=2)
    print("📤 JSON Output (by_alias=True) - What Spring Boot receives:")
    print(json_output)
    
    return json_output

def test_failure_message_format():
    """Test the JSON output format for failure messages"""
    print("\n🧪 Testing Failure Message JSON Format...")
    
    failure_message = ProcessFailureMessage(
        content_id="test-content-id",
        content_type=ContentType.DOCUMENT,
        error_message="Failed to parse PDF: corrupted file",
        error_code="PDF_PARSE_ERROR",
        stack_trace="Traceback...",
        retry_count=1,
        failed_step="pdf_extraction"
    )
    
    # Test with by_alias=True (what we send to Spring Boot)
    json_output = failure_message.model_dump_json(by_alias=True, indent=2)
    print("📤 JSON Output (by_alias=True) - What Spring Boot receives:")
    print(json_output)
    
    return json_output

if __name__ == "__main__":
    print("🔍 Testing JSON Output Formats for Spring Boot Compatibility\n")
    
    success_json = test_success_message_format()
    failure_json = test_failure_message_format()
    
    print("\n✅ JSON format test completed!")
    print("📋 Verify these match your Spring Boot expectations")