from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class EventType(str, Enum):
    CONTENT_PROCESS_REQUEST = "content.process.request"
    CONTENT_PROCESS_SUCCESS = "content.process.success"
    CONTENT_PROCESS_FAILED = "content.process.failed"


class ContentType(str, Enum):
    DOCUMENT = "document"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"


class BaseMessage(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), alias="eventId")
    event_type: EventType = Field(alias="eventType")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), alias="timestamp")
    content_id: str = Field(alias="contentId")
    content_type: ContentType = Field(alias="contentType")
    
    model_config = {"populate_by_name": True}


class ProcessRequestMessage(BaseMessage):
    event_type: EventType = Field(default=EventType.CONTENT_PROCESS_REQUEST, alias="eventType")
    file_name: str = Field(alias="fileName")
    s3_key: str = Field(alias="s3Key")
    s3_bucket: str = Field(alias="s3Bucket")
    mime_type: str = Field(alias="mimeType")
    file_size: int = Field(alias="fileSize")
    project_id: str = Field(alias="projectId")
    user_id: str = Field(alias="userId")


class ProcessSuccessMessage(BaseMessage):
    event_type: EventType = Field(default=EventType.CONTENT_PROCESS_SUCCESS, alias="eventType")
    message: str = Field(alias="message")
    processing_time_ms: int = Field(alias="processingTimeMs")
    chunk_count: int = Field(alias="chunkCount")
    s3_bucket_name: str = Field(alias="s3BucketName")
    s3_key: str = Field(alias="s3Key")


class ProcessFailureMessage(BaseMessage):
    event_type: EventType = Field(default=EventType.CONTENT_PROCESS_FAILED, alias="eventType")
    error_message: str = Field(alias="errorMessage")
    error_code: str = Field(alias="errorCode")
    stack_trace: Optional[str] = Field(default=None, alias="stackTrace")
    retry_count: int = Field(default=0, alias="retryCount")
    failed_step: str = Field(alias="failedStep")


class SpringAIDocument(BaseModel):
    content: str
    metadata: Dict[str, Any]