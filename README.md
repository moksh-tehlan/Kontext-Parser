# Kontext Processor

A production-level Python application for processing documents through AWS SQS queues with clean architecture.

## Architecture

The application follows clean architecture principles with clear separation of concerns:

```
src/
├── config/         # Configuration management
├── models/         # Data models and DTOs
├── repositories/   # Data access layer (SQS operations)
├── services/       # Business logic services
├── use_cases/      # Application use cases
└── exceptions/     # Custom exceptions
```

## Features

- **AWS SQS Integration**: Consumes from `kontext-process-queue` and sends responses to `kontext-processing-queue`
- **Type Safety**: Uses Pydantic models for message validation
- **Error Handling**: Comprehensive error handling with proper error codes
- **Clean Architecture**: Separation of concerns with dependency injection
- **Production Ready**: Logging, configuration management, and proper exception handling

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables in `.env.dev`:
```bash
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_REGION=ap-south-1
PROCESS_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/221082203234/kontext-process-queue
PROCESSING_QUEUE_URL=https://sqs.ap-south-1.amazonaws.com/221082203234/kontext-processing-queue
MAX_MESSAGES=10
WAIT_TIME_SECONDS=20
S3_BUCKET_NAME=kontext-dev-bucket
```

3. Run the application:
```bash
python main.py
```

## Message Flow

### Input Message (kontext-process-queue)
```json
{
  "eventId": "uuid-string",
  "eventType": "content.process.request",
  "timestamp": "2024-01-15T10:30:00",
  "contentId": "document-uuid",
  "contentType": "document",
  "fileName": "example.pdf",
  "s3Key": "documents/example.pdf",
  "s3Bucket": "kontext-dev-bucket",
  "mimeType": "application/pdf",
  "fileSize": 1234567,
  "projectId": "project-uuid",
  "userId": "user-uuid"
}
```

### Success Response (kontext-processing-queue)
```json
{
  "eventId": "new-uuid",
  "eventType": "content.process.success",
  "timestamp": "2024-01-15T10:35:00",
  "contentId": "same-document-uuid-from-request",
  "contentType": "document",
  "message": "Document processed successfully",
  "processingTimeMs": 30000,
  "chunkCount": 15,
  "s3BucketName": "kontext-dev-bucket",
  "s3Key": "processed/document-uuid-chunks.json"
}
```

### Failure Response (kontext-processing-queue)
```json
{
  "eventId": "new-uuid",
  "eventType": "content.process.failed",
  "timestamp": "2024-01-15T10:32:00",
  "contentId": "same-document-uuid-from-request",
  "contentType": "document",
  "errorMessage": "Failed to parse PDF: corrupted file",
  "errorCode": "PDF_PARSE_ERROR",
  "stackTrace": "optional-stack-trace",
  "retryCount": 1,
  "failedStep": "pdf_extraction"
}
```

## Components

### Models (`src/models/messages.py`)
- **ProcessRequestMessage**: Input message structure
- **ProcessSuccessMessage**: Success response structure
- **ProcessFailureMessage**: Failure response structure
- **SpringAIDocument**: Document chunk structure for Spring AI

### Repositories (`src/repositories/sqs_repository.py`)
- **SQSRepository**: Handles all SQS operations (receive, send, delete messages)

### Services
- **DocumentService** (`src/services/document_service.py`): Document processing logic (currently mocked)
- **S3Service** (`src/services/s3_service.py`): S3 file operations

### Use Cases (`src/use_cases/message_processor.py`)
- **MessageProcessor**: Main application logic that orchestrates the entire flow

## Next Steps

1. Replace `MockDocumentService` with actual document processing logic
2. Add support for different document types (PDF, DOCX, TXT, etc.)
3. Implement retry mechanisms for failed messages
4. Add monitoring and metrics
5. Add unit and integration tests