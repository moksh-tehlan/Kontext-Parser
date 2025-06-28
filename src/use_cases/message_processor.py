import json
import logging
import traceback
from typing import Dict, Any
from datetime import datetime

from src.models.messages import (
    ProcessRequestMessage, 
    ProcessSuccessMessage, 
    ProcessFailureMessage,
    EventType
)
from src.repositories.sqs_repository import SQSRepositoryInterface
from src.handler import Handler
from src.services.s3_service import S3ServiceInterface
from src.config.settings import AppConfig
from src.exceptions.processing_exceptions import ProcessingException

logger = logging.getLogger(__name__)


class MessageProcessor:
    def __init__(
        self,
        config: AppConfig,
        sqs_repository: SQSRepositoryInterface,
        handler: Handler,
        s3_service: S3ServiceInterface
    ):
        self.config = config
        self.sqs_repository = sqs_repository
        self.handler = handler
        self.s3_service = s3_service
    
    def process_messages(self) -> None:
        try:
            messages = self.sqs_repository.receive_messages(
                queue_url=self.config.sqs.process_queue_url,
                max_messages=self.config.sqs.max_messages
            )
            
            for message in messages:
                self._process_single_message(message)
                
        except Exception as e:
            logger.error(f"Error in message processing loop: {e}")
    
    def _process_single_message(self, message: Dict[str, Any]) -> None:
        try:
            # Parse message body
            message_body = json.loads(message['Body'])
            request = ProcessRequestMessage(**message_body)
            
            logger.info(f"Processing request for content ID: {request.content_id}")
            
            # Process the request using handler
            start_time = datetime.utcnow()
            processed_documents = self.handler.handle(request)
            end_time = datetime.utcnow()
            processing_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Upload processed documents to S3
            s3_key = self.s3_service.upload_processed_documents(
                documents=processed_documents,
                content_id=request.content_id
            )
            
            # Send success response
            success_message = ProcessSuccessMessage(
                content_id=request.content_id,
                content_type=request.content_type,
                message="Document processed successfully",
                processing_time_ms=processing_time_ms,
                chunk_count=len(processed_documents),
                s3_bucket_name=self.config.s3.bucket_name,
                s3_key=s3_key
            )
            
            self.sqs_repository.send_message(
                queue_url=self.config.sqs.processing_queue_url,
                message=success_message
            )
            
            # Delete the processed message
            self.sqs_repository.delete_message(
                queue_url=self.config.sqs.process_queue_url,
                receipt_handle=message['ReceiptHandle']
            )
            
            logger.info(f"Successfully processed content ID: {request.content_id}")
            
        except ProcessingException as e:
            self._handle_processing_error(message, e)
        except Exception as e:
            self._handle_unexpected_error(message, e)
    
    def _handle_processing_error(self, message: Dict[str, Any], error: ProcessingException) -> None:
        try:
            message_body = json.loads(message['Body'])
            request = ProcessRequestMessage(**message_body)
            
            failure_message = ProcessFailureMessage(
                content_id=request.content_id,
                content_type=request.content_type,
                error_message=str(error),
                error_code=error.error_code,
                stack_trace=traceback.format_exc(),
                retry_count=0,
                failed_step=error.failed_step
            )
            
            self.sqs_repository.send_message(
                queue_url=self.config.sqs.processing_queue_url,
                message=failure_message
            )
            
            logger.error(f"Processing failed for content ID: {request.content_id}")
            
        except Exception as e:
            logger.error(f"Error handling processing error: {e}")
    
    def _handle_unexpected_error(self, message: Dict[str, Any], error: Exception) -> None:
        try:
            message_body = json.loads(message['Body'])
            content_id = message_body.get('contentId', 'unknown')
            content_type = message_body.get('contentType', 'document')
            
            failure_message = ProcessFailureMessage(
                content_id=content_id,
                content_type=content_type,
                error_message=f"Unexpected error: {str(error)}",
                error_code="UNEXPECTED_ERROR",
                stack_trace=traceback.format_exc(),
                retry_count=0,
                failed_step="message_processing"
            )
            
            self.sqs_repository.send_message(
                queue_url=self.config.sqs.processing_queue_url,
                message=failure_message
            )
            
            logger.error(f"Unexpected error processing message: {error}")
            
        except Exception as e:
            logger.critical(f"Critical error in error handling: {e}")
    
    def run_continuously(self) -> None:
        logger.info("Starting message processor...")
        
        while True:
            try:
                self.process_messages()
            except KeyboardInterrupt:
                logger.info("Received interrupt signal. Shutting down...")
                break
            except Exception as e:
                logger.error(f"Error in main processing loop: {e}")
                continue