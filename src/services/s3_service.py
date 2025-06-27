from abc import ABC, abstractmethod
from typing import List
import boto3
import json
import logging
from botocore.exceptions import ClientError

from src.config.settings import AppConfig
from src.models.messages import SpringAIDocument
from src.exceptions.processing_exceptions import S3UploadException, S3DownloadException

logger = logging.getLogger(__name__)


class S3ServiceInterface(ABC):
    @abstractmethod
    def upload_processed_documents(self, documents: List[SpringAIDocument], content_id: str) -> str:
        pass
    
    @abstractmethod
    def download_file(self, s3_key: str, s3_bucket: str) -> bytes:
        pass


class S3Service(S3ServiceInterface):
    def __init__(self, config: AppConfig):
        self.config = config
        self.s3_client = boto3.client(
            's3',
            region_name=config.aws.region,
            aws_access_key_id=config.aws.access_key_id,
            aws_secret_access_key=config.aws.secret_access_key
        )
    
    def upload_processed_documents(self, documents: List[SpringAIDocument], content_id: str) -> str:
        try:
            # Convert documents to dict format
            documents_dict = [doc.dict() for doc in documents]
            documents_json = json.dumps(documents_dict, indent=2)
            
            # Generate S3 key for processed documents
            s3_key = f"processed/{content_id}-chunks.json"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.config.s3.bucket_name,
                Key=s3_key,
                Body=documents_json,
                ContentType='application/json'
            )
            
            logger.info(f"Successfully uploaded processed documents to s3://{self.config.s3.bucket_name}/{s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Error uploading to S3: {e}")
            raise S3UploadException(f"Failed to upload processed documents: {str(e)}")
    
    def download_file(self, s3_key: str, s3_bucket: str) -> bytes:
        try:
            response = self.s3_client.get_object(
                Bucket=s3_bucket,
                Key=s3_key
            )
            
            file_content = response['Body'].read()
            logger.info(f"Successfully downloaded file from s3://{s3_bucket}/{s3_key}")
            return file_content
            
        except ClientError as e:
            logger.error(f"Error downloading from S3: {e}")
            raise S3DownloadException(f"Failed to download file {s3_key}: {str(e)}")