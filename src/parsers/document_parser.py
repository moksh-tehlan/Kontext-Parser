import pymupdf
import tempfile
import os
import logging
from typing import List, Dict, Any
from chonkie import SentenceChunker
from .base_parser import BaseParser
from ..models.messages import SpringAIDocument, ProcessRequestMessage
from ..services.s3_service import S3ServiceInterface

logger = logging.getLogger(__name__)


class DocumentParser(BaseParser):
    """
    Document parser implementation using PyMuPDF library.
    
    Handles S3 download, document parsing, and chunking into SpringAI documents.
    """
    
    def __init__(self, s3_service: S3ServiceInterface):
        """
        Initialize the DocumentParser.
        
        Args:
            s3_service: S3 service for downloading files
        """
        self.s3_service = s3_service
    
    def parse(self, request: ProcessRequestMessage, chunk_size: int = 512, overlap: int = 128) -> List[SpringAIDocument]:
        """
        Parse a document from ProcessRequestMessage and return chunked SpringAI documents.
        
        Args:
            request: The processing request containing S3 info and metadata
            chunk_size: Maximum tokens per chunk (default: 512)
            overlap: Number of tokens to overlap between chunks (default: 128)
            
        Returns:
            List[SpringAIDocument]: List of document chunks with metadata
            
        Raises:
            Exception: If parsing fails
        """
        temp_file_path = None
        try:
            logger.info(f"Processing document: {request.file_name} from S3")
            
            # Download file from S3
            file_content = self.s3_service.download_file(
                s3_key=request.s3_key,
                s3_bucket=request.s3_bucket
            )
            
            # Create temporary file with proper extension
            file_extension = request.file_name.split('.')[-1] if '.' in request.file_name else 'bin'
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            logger.debug(f"Downloaded file to: {temp_file_path}")
            
            # Parse the document
            doc = pymupdf.open(temp_file_path)
            
            # Extract document metadata
            doc_metadata = {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "subject": doc.metadata.get("subject", ""),
                "creator": doc.metadata.get("creator", ""),
                "producer": doc.metadata.get("producer", ""),
                "creation_date": doc.metadata.get("creationDate", ""),
                "modification_date": doc.metadata.get("modDate", ""),
                "total_pages": len(doc),
                "source": request.file_name
            }
            
            # Initialize Chonkie SentenceChunker
            chunker = SentenceChunker(
                tokenizer_or_token_counter="gpt2",
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                min_sentences_per_chunk=1
            )
            
            spring_ai_documents = []
            global_chunk_index = 0
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text().strip()
                page_number = page_num + 1  # 1-indexed page numbers
                
                if not page_text:  # Skip empty pages
                    continue
                
                # Extract page metadata
                page_metadata = {
                    "page_width": page.rect.width,
                    "page_height": page.rect.height,
                    "page_rotation": page.rotation,
                }
                
                # Add image count if any
                image_list = page.get_images()
                if image_list:
                    page_metadata["page_image_count"] = len(image_list)
                
                # Use Chonkie to chunk the page text
                chonkie_chunks = chunker.chunk(page_text)
                
                for chonkie_chunk in chonkie_chunks:
                    # Create comprehensive metadata for this chunk
                    chunk_metadata = {
                        "page_number": page_number,
                        "chunk_index": global_chunk_index,
                        "token_count": chonkie_chunk.token_count,
                        "chunk_start_index": chonkie_chunk.start_index,
                        "chunk_end_index": chonkie_chunk.end_index,
                        # Request metadata
                        "knowledge_id": request.content_id,
                        "project_id": request.project_id,
                        "user_id": request.user_id,
                        "file_name": request.file_name,
                        "mime_type": request.mime_type,
                        "file_size": request.file_size,
                        "s3_bucket": request.s3_bucket,
                        "s3_key": request.s3_key,
                        "processing_timestamp": request.timestamp
                    }
                    
                    # Add document metadata with doc_ prefix
                    chunk_metadata.update({
                        f"doc_{key}": value for key, value in doc_metadata.items()
                        if value  # Only add non-empty values
                    })
                    
                    # Add page metadata
                    chunk_metadata.update(page_metadata)
                    
                    # Create SpringAIDocument
                    spring_ai_doc = SpringAIDocument(
                        content=chonkie_chunk.text,
                        metadata=chunk_metadata
                    )
                    spring_ai_documents.append(spring_ai_doc)
                    global_chunk_index += 1
            
            doc.close()
            logger.info(f"Successfully processed document into {len(spring_ai_documents)} chunks")
            return spring_ai_documents
            
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise Exception(f"Failed to parse document {request.file_name}: {str(e)}")
            
        finally:
            # Clean up temporary file
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                    logger.debug(f"Cleaned up temporary file: {temp_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to clean up temporary file: {e}")
