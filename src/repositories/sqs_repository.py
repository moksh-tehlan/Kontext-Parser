import json
import logging
import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Union
import boto3
from botocore.exceptions import ClientError

from src.models.messages import ProcessSuccessMessage, ProcessFailureMessage
from src.config.settings import AppConfig

logger = logging.getLogger(__name__)


class SQSRepositoryInterface(ABC):
    """Interface for SQS operations"""
    
    @abstractmethod
    def send_message(self, queue_url: str, message: Union[ProcessSuccessMessage, ProcessFailureMessage, Dict[str, Any]]) -> None:
        """Send a message to the specified SQS queue"""
        pass


class SQSRepository(SQSRepositoryInterface):
    def __init__(self, config: AppConfig):
        self.config = config
        # Initialize SQS client with conditional credentials
        if os.environ.get('AWS_LAMBDA_FUNCTION_NAME'):
            # Use IAM role in Lambda
            self.sqs_client = boto3.client('sqs')
        else:
            # Use explicit credentials for local/development
            self.sqs_client = boto3.client(
                'sqs',
                region_name=config.aws.region,
                aws_access_key_id=config.aws.access_key_id,
                aws_secret_access_key=config.aws.secret_access_key
            )
    
    def send_message(self, queue_url: str, message: Union[ProcessSuccessMessage, ProcessFailureMessage, Dict[str, Any]]) -> None:
        """Send a message to the specified SQS queue"""
        try:
            message_body = message.model_dump_json(by_alias=True)
            
            response = self.sqs_client.send_message(
                QueueUrl=queue_url,
                MessageBody=message_body
            )
            
            logger.info(f"Message sent to queue {queue_url}: {response['MessageId']}")

        except ClientError as e:
            logger.error(f"Failed to send message to queue {queue_url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error sending message to queue {queue_url}: {e}")
            raise