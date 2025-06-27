from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import boto3
import json
import logging
from botocore.exceptions import ClientError

from src.config.settings import AppConfig
from src.models.messages import BaseMessage
from src.exceptions.processing_exceptions import SQSMessageException

logger = logging.getLogger(__name__)


class SQSRepositoryInterface(ABC):
    @abstractmethod
    def receive_messages(self, queue_url: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    def send_message(self, queue_url: str, message: BaseMessage) -> bool:
        pass
    
    @abstractmethod
    def delete_message(self, queue_url: str, receipt_handle: str) -> bool:
        pass


class SQSRepository(SQSRepositoryInterface):
    def __init__(self, config: AppConfig):
        self.config = config
        self.sqs_client = boto3.client(
            'sqs',
            region_name=config.aws.region,
            aws_access_key_id=config.aws.access_key_id,
            aws_secret_access_key=config.aws.secret_access_key
        )
    
    def receive_messages(self, queue_url: str, max_messages: int = 10) -> List[Dict[str, Any]]:
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=self.config.sqs.wait_time_seconds,
                AttributeNames=['All'],
                MessageAttributeNames=['All']
            )
            
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from queue")
            return messages
            
        except ClientError as e:
            logger.error(f"Error receiving messages from SQS: {e}")
            raise SQSMessageException(f"Failed to receive messages: {str(e)}")
    
    def send_message(self, queue_url: str, message: BaseMessage) -> bool:
        try:
            message_body = message.model_dump_json(by_alias=True)
            
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body
            )
            
            message_id = response.get('MessageId')
            logger.info(f"Message sent successfully with ID: {message_id}")
            return True
            
        except ClientError as e:
            logger.error(f"Error sending message to SQS: {e}")
            raise SQSMessageException(f"Failed to send message: {str(e)}")
    
    def delete_message(self, queue_url: str, receipt_handle: str) -> bool:
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle
            )
            
            logger.info("Message deleted successfully from queue")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting message from SQS: {e}")
            raise SQSMessageException(f"Failed to delete message: {str(e)}")