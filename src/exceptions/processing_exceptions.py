class ProcessingException(Exception):
    def __init__(self, message: str, error_code: str, failed_step: str):
        super().__init__(message)
        self.error_code = error_code
        self.failed_step = failed_step


class DocumentProcessingException(ProcessingException):
    def __init__(self, message: str, failed_step: str = "document_processing"):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR", failed_step)


class S3UploadException(ProcessingException):
    def __init__(self, message: str, failed_step: str = "s3_upload"):
        super().__init__(message, "S3_UPLOAD_ERROR", failed_step)


class S3DownloadException(ProcessingException):
    def __init__(self, message: str, failed_step: str = "s3_download"):
        super().__init__(message, "S3_DOWNLOAD_ERROR", failed_step)


class SQSMessageException(ProcessingException):
    def __init__(self, message: str, failed_step: str = "sqs_message"):
        super().__init__(message, "SQS_MESSAGE_ERROR", failed_step)