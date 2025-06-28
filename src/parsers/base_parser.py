from abc import ABC, abstractmethod
from typing import List, Any, Optional
from ..models.messages import SpringAIDocument, ProcessRequestMessage


class BaseParser(ABC):
    """
    Abstract base class for content parsers.
    
    This class defines the interface that all parsers must implement.
    """
    
    @abstractmethod
    def parse(self, request: ProcessRequestMessage, chunk_size: int = 512, overlap: int = 128) -> List[SpringAIDocument]:
        """
        Parse content from a ProcessRequestMessage and return chunked SpringAI documents.
        
        Args:
            request (ProcessRequestMessage): The processing request containing S3 info and metadata
            chunk_size (int): Maximum tokens per chunk (default: 512)
            overlap (int): Number of tokens to overlap between chunks (default: 128)
            
        Returns:
            List[SpringAIDocument]: List of content chunks with metadata
            
        Raises:
            Exception: If parsing fails
        """
        pass