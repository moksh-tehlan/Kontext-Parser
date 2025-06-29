import json
import logging
import os
import traceback
from typing import Dict, Any, List
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

from src.handler import Handler
from src.services.s3_service import S3Service
from src.models.messages import ProcessRequestMessage, ProcessSuccessMessage, ProcessFailureMessage
from src.exceptions.processing_exceptions import ProcessingException
from src.config.settings import AppConfig

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Initialize services lazily to avoid init timeout
config = None
s3_service = None
sqs_client = None
handler = None

def get_handler():
    global config, s3_service, sqs_client, handler
    if handler is None:
        config = AppConfig()
        s3_service = S3Service(config)
        # Initialize SQS client for sending success messages
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            sqs_client = boto3.client('sqs')  # Use IAM role in Lambda
        else:
            sqs_client = boto3.client('sqs', 
                region_name=config.aws.region,
                aws_access_key_id=config.aws.access_key_id,
                aws_secret_access_key=config.aws.secret_access_key
            )
        handler = Handler(s3_service)
    return handler, s3_service, sqs_client, config


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for processing SQS events containing document processing requests.
    
    Args:
        event: SQS event containing Records array
        context: Lambda context object
        
    Returns:
        Dict containing processing results and any failures
    """
    logger.info("=== LAMBDA HANDLER STARTED ===")
    logger.info(f"Raw event received: {json.dumps(event)}")
    logger.info(f"Event type: {type(event)}")
    logger.info(f"Event keys: {list(event.keys()) if isinstance(event, dict) else 'Not a dict'}")
    
    records = event.get('Records', [])
    logger.info(f"Found {len(records)} records in event")
    
    results = []
    failures = []
    
    for i, record in enumerate(records):
        logger.info(f"=== Processing record {i+1}/{len(records)} ===")
        logger.info(f"Record keys: {list(record.keys()) if isinstance(record, dict) else 'Not a dict'}")
        logger.info(f"Message ID: {record.get('messageId', 'MISSING')}")
        logger.info(f"Event source: {record.get('eventSource', 'MISSING')}")
        logger.info(f"Raw body: {record.get('body', 'MISSING')}")
        logger.info(f"Body type: {type(record.get('body'))}")
        try:
            # Parse SQS message
            logger.info("Parsing JSON from record body...")
            message_body = json.loads(record['body'])
            logger.info(f"Parsed message body: {json.dumps(message_body)}")
            logger.info(f"Message name: {message_body.get('name', 'MISSING')}")
            logger.info(f"Message contentType: {message_body.get('contentType', 'MISSING')}")
            
            # Convert to ProcessRequestMessage
            logger.info("Converting to ProcessRequestMessage...")
            request = ProcessRequestMessage(**message_body)
            logger.info(f"ProcessRequestMessage created: {request.name}, type: {request.content_type}")
            
            # Process the request (same as message_processor.py:56-60)
            logger.info(f"Processing request for content ID: {request.content_id}")
            handler, s3_service, sqs_client, config = get_handler()
            
            start_time = datetime.utcnow()
            processed_documents = handler.handle(request)
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            logger.info(f"Handler processing completed, got {len(processed_documents)} documents")
            
            # Upload processed documents to S3 (same as message_processor.py:62-66)
            logger.info("Uploading processed documents to S3...")
            s3_key = s3_service.upload_processed_documents(
                documents=processed_documents,
                content_id=request.content_id
            )
            logger.info(f"Documents uploaded to S3: {s3_key}")
            
            # Send success response (same as message_processor.py:68-77)
            logger.info("Sending success message to processing queue...")
            success_message = ProcessSuccessMessage(
                contentId=request.content_id,
                contentType=request.content_type,
                message="Document processed successfully",
                processingTimeMs=processing_time_ms,
                chunkCount=len(processed_documents),
                s3BucketName=config.s3.bucket_name,
                s3Key=s3_key
            )
            
            # Send to processing queue (same as message_processor.py:79-82)
            sqs_client.send_message(
                QueueUrl=config.sqs.processing_queue_url,
                MessageBody=success_message.model_dump_json(by_alias=True)
            )
            
            # Lambda automatically deletes SQS message on success (no need for manual delete)
            logger.info(f"Successfully processed content ID: {request.content_id}")
            logger.info(f"Processing time: {processing_time_ms}ms, Chunks: {len(processed_documents)}")
            
            results.append({
                'messageId': record.get('messageId'),
                'name': request.name,
                'contentType': request.content_type.value,
                'chunksGenerated': len(processed_documents),
                'status': 'success'
            })
            
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in SQS message: {str(e)}"
            logger.error(error_msg)
            failures.append({
                'messageId': record.get('messageId'),
                'error': error_msg,
                'errorType': 'JSON_DECODE_ERROR'
            })
            
        except ProcessingException as e:
            # Handle processing error (same as message_processor.py:97-120)
            logger.error(f"Processing failed for message {record.get('messageId')}: {str(e)}")
            try:
                message_body = json.loads(record['body'])
                request = ProcessRequestMessage(**message_body)
                
                handler, s3_service, sqs_client, config = get_handler()
                
                failure_message = ProcessFailureMessage(
                    contentId=request.content_id,
                    contentType=request.content_type,
                    errorMessage=str(e),
                    errorCode=e.error_code,
                    stackTrace=traceback.format_exc(),
                    retryCount=0,
                    failedStep=e.failed_step
                )
                
                sqs_client.send_message(
                    QueueUrl=config.sqs.processing_queue_url,
                    MessageBody=failure_message.model_dump_json(by_alias=True)
                )
                
                logger.error(f"Processing failed for content ID: {request.content_id}")
                
            except Exception as send_error:
                logger.error(f"Error sending failure message: {send_error}")
            
            failures.append({
                'messageId': record.get('messageId'),
                'error': str(e),
                'errorType': 'PROCESSING_ERROR',
                'errorCode': e.error_code,
                'failedStep': e.failed_step
            })
            
        except Exception as e:
            # Handle unexpected error (same as message_processor.py:122-147)
            logger.error(f"Unexpected error processing message {record.get('messageId')}: {str(e)}")
            try:
                message_body = json.loads(record['body'])
                content_id = message_body.get('contentId', 'unknown')
                content_type = message_body.get('contentType', 'document')
                
                handler, s3_service, sqs_client, config = get_handler()
                
                failure_message = ProcessFailureMessage(
                    contentId=content_id,
                    contentType=content_type,
                    errorMessage=f"Unexpected error: {str(e)}",
                    errorCode="UNEXPECTED_ERROR",
                    stackTrace=traceback.format_exc(),
                    retryCount=0,
                    failedStep="message_processing"
                )
                
                sqs_client.send_message(
                    QueueUrl=config.sqs.processing_queue_url,
                    MessageBody=failure_message.model_dump_json(by_alias=True)
                )
                
                logger.error(f"Unexpected error processing message: {e}")
                
            except Exception as send_error:
                logger.critical(f"Critical error in error handling: {send_error}")
            
            failures.append({
                'messageId': record.get('messageId'),
                'error': str(e),
                'errorType': 'UNEXPECTED_ERROR'
            })
    
    # Return results
    response = {
        'statusCode': 200 if not failures else 207,  # 207 for partial success
        'processedCount': len(results),
        'failureCount': len(failures),
        'results': results
    }
    
    if failures:
        response['failures'] = failures
        logger.warning(f"Processing completed with {len(failures)} failures out of {len(event.get('Records', []))} records")
    else:
        logger.info(f"All {len(results)} records processed successfully")
    
    return response


def batch_failure_handler(failures: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Handle batch failures for SQS partial batch failure reporting.
    
    Args:
        failures: List of failed message details
        
    Returns:
        Dict formatted for SQS batch failure reporting
    """
    failed_message_ids = [failure.get('messageId') for failure in failures if failure.get('messageId')]
    
    return {
        'batchItemFailures': [
            {'itemIdentifier': message_id} for message_id in failed_message_ids
        ]
    }