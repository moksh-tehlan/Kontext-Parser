import asyncio
import logging
from typing import List, Dict, Any
from chonkie import SentenceChunker
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from .base_parser import BaseParser
from ..models.messages import SpringAIDocument, ProcessRequestMessage

logger = logging.getLogger(__name__)


class WebParser(BaseParser):
    """
    Web parser implementation using Crawl4AI library.
    
    Handles web URL crawling and content extraction into SpringAI documents.
    """
    
    def __init__(self):
        """Initialize the WebParser."""
        pass
    
    def parse(self, request: ProcessRequestMessage, chunk_size: int = 512, overlap: int = 128) -> List[SpringAIDocument]:
        """
        Parse a web URL from ProcessRequestMessage and return chunked SpringAI documents.
        
        Args:
            request: The processing request containing web URL and metadata
            chunk_size: Maximum tokens per chunk (default: 512)
            overlap: Number of tokens to overlap between chunks (default: 128)
            
        Returns:
            List[SpringAIDocument]: List of web content chunks with metadata
            
        Raises:
            Exception: If crawling fails
        """
        try:
            logger.info(f"Processing web URL: {request.web_url}")
            
            # Run the async crawling
            try:
                loop = asyncio.get_running_loop()
                # If we're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._crawl_url(request.web_url))
                    web_content = future.result()
            except RuntimeError:
                # No running loop, safe to use asyncio.run
                web_content = asyncio.run(self._crawl_url(request.web_url))
            
            if not web_content:
                raise Exception("Failed to extract content from web URL")
            
            # Extract metadata from the crawl result
            web_metadata = {
                "url": request.web_url,
                "title": web_content.get("title", ""),
                "source": request.web_url,
                "content_length": len(web_content.get("markdown", "")),
                "success": web_content.get("success", False)
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
            
            # Get the markdown content for chunking
            content_text = web_content.get("markdown", "").strip()
            
            if not content_text:
                logger.warning(f"No content extracted from URL: {request.s3_key}")
                return []
            
            # Use Chonkie to chunk the web content
            chonkie_chunks = chunker.chunk(content_text)
            
            for chonkie_chunk in chonkie_chunks:
                # Create metadata with important generic fields first
                chunk_metadata = {
                    # Important generic fields for all parsers
                    "knowledge_id": request.content_id,
                    "processing_timestamp": request.timestamp,
                    # "project_id": request.project_id,
                    # "user_id": request.user_id,
                    "name": request.name,
                    "mime_type": request.mime_type,
                    # "file_size": request.file_size,
                    "url":request.web_url,
                    # "s3_bucket": request.s3_bucket,
                    # "s3_key": request.s3_key,  # This is the URL for web content
                    
                    # Chunking metadata
                    "chunk_index": global_chunk_index,
                    "token_count": chonkie_chunk.token_count,
                    "chunk_start_index": chonkie_chunk.start_index,
                    "chunk_end_index": chonkie_chunk.end_index,
                    
                    # Format-specific data in additional_payload
                    "additional_payload": {
                        # Web-specific metadata
                        "url": web_metadata["url"],
                        "web_title": web_metadata["title"],
                        "content_length": web_metadata["content_length"],
                        "crawl_success": web_metadata["success"]
                    }
                }
                
                # Create SpringAIDocument
                spring_ai_doc = SpringAIDocument(
                    content=chonkie_chunk.text,
                    metadata=chunk_metadata
                )
                spring_ai_documents.append(spring_ai_doc)
                global_chunk_index += 1
            
            logger.info(f"Successfully processed web URL into {len(spring_ai_documents)} chunks")
            return spring_ai_documents
            
        except Exception as e:
            logger.error(f"Error processing web URL: {e}")
            raise Exception(f"Failed to parse web URL {request.s3_key}: {str(e)}")
    
    async def _crawl_url(self, url: str) -> Dict[str, Any]:
        """
        Crawl a URL using Crawl4AI and extract content.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Dict containing the crawled content and metadata
        """
        try:
            # Configure browser for crawling
            browser_config = BrowserConfig(
                verbose=True,  # Enable verbose for debugging
                headless=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            # Configure crawling behavior with minimal settings
            run_config = CrawlerRunConfig(
                word_count_threshold=1,
                exclude_external_links=False,
                cache_mode=CacheMode.DISABLED,
                page_timeout=20000,  # 20 seconds timeout
                delay_before_return_html=1.0,  # Wait 1 second
                screenshot=False,
                pdf=False
            )
            
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)
                
                logger.info(f"Crawl result for {url}: success={result.success}")
                if hasattr(result, 'markdown') and result.markdown:
                    logger.info(f"Markdown length: {len(result.markdown)}")
                if hasattr(result, 'html') and result.html:
                    logger.info(f"HTML length: {len(result.html)}")
                
                return {
                    "success": result.success,
                    "markdown": result.markdown if hasattr(result, 'markdown') and result.markdown else "",
                    "title": result.metadata.get('title', '') if hasattr(result, 'metadata') and result.metadata else "",
                    "html": result.html if hasattr(result, 'html') and result.html else "",
                    "status_code": result.status_code if hasattr(result, 'status_code') else None,
                    "error_message": result.error_message if hasattr(result, 'error_message') and not result.success else ""
                }
                
        except Exception as e:
            logger.error(f"Crawl4AI error for URL {url}: {e}")
            return {
                "success": False,
                "markdown": "",
                "title": "",
                "html": "",
                "status_code": None,
                "error_message": str(e)
            }