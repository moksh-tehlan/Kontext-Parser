from abc import ABC, abstractmethod
from typing import List
import time
import random
import logging

from src.models.messages import SpringAIDocument, SpringAIDocumentMetadata, ProcessRequestMessage
from src.exceptions.processing_exceptions import DocumentProcessingException

logger = logging.getLogger(__name__)


class DocumentServiceInterface(ABC):
    @abstractmethod
    def process_document(self, request: ProcessRequestMessage) -> List[SpringAIDocument]:
        pass


class MockDocumentService(DocumentServiceInterface):
    def process_document(self, request: ProcessRequestMessage) -> List[SpringAIDocument]:
        try:
            logger.info(f"Processing document: {request.file_name}")
            
            # Simulate processing time
            time.sleep(2)
            
            # Mock document chunks
            chunks = []
            chunk_count = random.randint(5, 20)
            
            for i in range(chunk_count):
                chunk = SpringAIDocument(
                    content=f"This is chunk {i+1} of document {request.file_name}. "
                           f"Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
                           f"Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
                    metadata=SpringAIDocumentMetadata(
                        knowledge_id=request.content_id,
                        title=request.file_name.replace('.pdf', '').replace('.txt', ''),
                        author="Mock Author",
                        chunk_index=i,
                        source=request.file_name
                    )
                )
                chunks.append(chunk)
            
            logger.info(f"Successfully processed document into {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise DocumentProcessingException(f"Failed to process document {request.file_name}: {str(e)}")