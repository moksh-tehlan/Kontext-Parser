from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

load_dotenv('.env.dev')


class AWSConfig(BaseSettings):
    access_key_id: str
    secret_access_key: str
    region: str = "ap-south-1"
    
    class Config:
        env_prefix = "AWS_"


class SQSConfig(BaseSettings):
    process_queue_url: str
    processing_queue_url: str
    max_messages: int = 10
    wait_time_seconds: int = 20
    
    class Config:
        env_prefix = ""


class S3Config(BaseSettings):
    bucket_name: str
    
    class Config:
        env_prefix = "S3_"


class AppConfig:
    def __init__(self):
        self.aws = AWSConfig()
        self.sqs = SQSConfig()
        self.s3 = S3Config()


def get_config() -> AppConfig:
    return AppConfig()