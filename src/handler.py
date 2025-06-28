import logging
from typing import List

from .models.messages import ProcessRequestMessage, SpringAIDocument, ContentType
from .parsers.document_parser import DocumentParser
from .services.s3_service import S3ServiceInterface
from .exceptions.processing_exceptions import ProcessingException

logger = logging.getLogger(__name__)


class Handler:
    """
    Simple handler that routes ProcessRequestMessage to appropriate parsers.
    """
    
    def __init__(self, s3_service: S3ServiceInterface):
        """
        Initialize the handler.
        
        Args:
            s3_service: S3 service to pass to parsers
        """
        # Initialize parsers with dependencies they need
        self.document_parser = DocumentParser(s3_service)
        # Future parsers:
        # self.image_parser = ImageParser(s3_service)
        # self.web_parser = WebParser()
    
    def handle(self, request: ProcessRequestMessage) -> List[SpringAIDocument]:
        """
        Route request to appropriate parser.
        
        Args:
            request: The content processing request
            
        Returns:
            List[SpringAIDocument]: Processed content chunks
            
        Raises:
            ProcessingException: If processing fails
        """
        try:
            logger.info(f"Routing {request.content_type} request: {request.file_name}")
            
            if request.content_type == ContentType.DOCUMENT:
                return self.document_parser.parse(request)
            elif request.content_type == ContentType.IMAGE:
                raise ProcessingException(
                    "Image processing not yet implemented",
                    error_code="NOT_IMPLEMENTED",
                    failed_step="parser_selection"
                )
            elif request.content_type == ContentType.VIDEO:
                raise ProcessingException(
                    "Video processing not yet implemented",
                    error_code="NOT_IMPLEMENTED", 
                    failed_step="parser_selection"
                )
            elif request.content_type == ContentType.AUDIO:
                raise ProcessingException(
                    "Audio processing not yet implemented",
                    error_code="NOT_IMPLEMENTED",
                    failed_step="parser_selection"
                )
            else:
                raise ProcessingException(
                    f"Unsupported content type: {request.content_type}",
                    error_code="UNSUPPORTED_CONTENT_TYPE",
                    failed_step="parser_selection"
                )
                
        except ProcessingException:
            # Re-raise processing exceptions as-is
            raise
        except Exception as e:
            logger.error(f"Unexpected error in handler: {e}")
            raise ProcessingException(
                f"Unexpected error processing request: {str(e)}",
                error_code="HANDLER_ERROR",
                failed_step="request_processing"
            )