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
            logger.info(f"=== WEB PARSER DEBUG START ===")
            logger.info(f"Processing web URL: {request.web_url}")
            logger.info(f"Request content_type: {request.content_type}")
            logger.info(f"Request name: {request.name}")
            
            # Run the async crawling
            logger.info("Starting web crawling...")
            try:
                loop = asyncio.get_running_loop()
                logger.info("Running in async context, using ThreadPoolExecutor")
                # If we're already in an async context, create a task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._crawl_url(request.web_url))
                    web_content = future.result()
            except RuntimeError:
                logger.info("No running async loop, using asyncio.run directly")
                # No running loop, safe to use asyncio.run
                web_content = asyncio.run(self._crawl_url(request.web_url))
            
            logger.info(f"Crawling completed. Result: {web_content}")
            
            if not web_content:
                logger.error("web_content is None or empty!")
                raise Exception("Failed to extract content from web URL")
            
            logger.info(f"Web content success: {web_content.get('success')}")
            logger.info(f"Web content keys: {list(web_content.keys())}")
            
            # Extract metadata from the crawl result
            web_metadata = {
                "url": request.web_url,
                "title": web_content.get("title", ""),
                "source": request.web_url,
                "content_length": len(web_content.get("markdown", "")),
                "success": web_content.get("success", False)
            }
            logger.info(f"Web metadata: {web_metadata}")
            
            # Get the markdown content for chunking
            content_text = web_content.get("markdown", "").strip()
            logger.info(f"Content text length: {len(content_text)}")
            logger.info(f"Content text preview (first 200 chars): {content_text[:200] if content_text else 'EMPTY'}")
            
            if not content_text:
                logger.warning(f"No content extracted from URL: {request.web_url}")
                logger.warning(f"Raw web_content: {web_content}")
                return []
            
            # Initialize Chonkie SentenceChunker
            logger.info("Initializing Chonkie SentenceChunker...")
            chunker = SentenceChunker(
                tokenizer_or_token_counter="gpt2",
                chunk_size=chunk_size,
                chunk_overlap=overlap,
                min_sentences_per_chunk=1
            )
            
            spring_ai_documents = []
            global_chunk_index = 0
            
            # Use Chonkie to chunk the web content
            logger.info("Starting content chunking...")
            chonkie_chunks = chunker.chunk(content_text)
            logger.info(f"Chonkie created {len(chonkie_chunks)} chunks")
            
            for chonkie_chunk in chonkie_chunks:
                logger.info(f"Processing chunk {global_chunk_index}: {len(chonkie_chunk.text)} chars")
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
            
            logger.info(f"=== WEB PARSER DEBUG END ===")
            logger.info(f"Successfully processed web URL into {len(spring_ai_documents)} chunks")
            return spring_ai_documents
            
        except Exception as e:
            logger.error(f"=== WEB PARSER ERROR ===")
            logger.error(f"Error processing web URL: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            raise Exception(f"Failed to parse web URL {request.web_url}: {str(e)}")
    
    async def _crawl_url(self, url: str) -> Dict[str, Any]:
        """
        Crawl a URL using Crawl4AI and extract content.
        
        Args:
            url: The URL to crawl
            
        Returns:
            Dict containing the crawled content and metadata
        """
        try:
            logger.info(f"=== CRAWL4AI DEBUG START for {url} ===")
            
            # Configure browser for crawling (Lambda-compatible)
            browser_config = BrowserConfig(
                verbose=False,  # Reduce verbosity for Lambda
                headless=True,
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                # Lambda-specific Chrome flags to handle sandbox restrictions
                extra_args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox", 
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-gpu-compositing",
                    "--disable-software-rasterizer",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                    "--disable-extensions",
                    "--disable-default-apps",
                    "--disable-sync",
                    "--metrics-recording-only",
                    "--no-first-run",
                    "--safebrowsing-disable-auto-update",
                    "--disable-component-extensions-with-background-pages",
                    "--disable-background-networking",
                    "--disable-component-update",
                    "--disable-client-side-phishing-detection",
                    "--disable-hang-monitor",
                    "--disable-popup-blocking",
                    "--disable-prompt-on-repost",
                    "--ignore-certificate-errors",
                    "--ignore-ssl-errors",
                    "--ignore-certificate-errors-spki-list",
                    "--disable-web-security",
                    "--allow-running-insecure-content",
                    "--disable-features=VizDisplayCompositor",
                    "--single-process"  # Run in single process mode for Lambda
                ]
            )
            logger.info(f"Browser config created")
            
            # Configure crawling behavior with minimal settings for Lambda
            run_config = CrawlerRunConfig(
                word_count_threshold=1,
                exclude_external_links=False,
                cache_mode=CacheMode.DISABLED,
                page_timeout=30000,  # 30 seconds timeout for Lambda
                delay_before_return_html=2.0,  # Wait 2 seconds for content to load
                screenshot=False,
                pdf=False,
                only_text=True,  # Extract only text content
            )
            logger.info(f"Run config created")
            
            logger.info("Creating AsyncWebCrawler...")
            async with AsyncWebCrawler(config=browser_config) as crawler:
                logger.info(f"Starting crawl for URL: {url}")
                result = await crawler.arun(url=url, config=run_config)
                
                logger.info(f"=== CRAWL RESULT ===")
                logger.info(f"URL: {url}")
                logger.info(f"Success: {result.success}")
                logger.info(f"Status code: {getattr(result, 'status_code', 'N/A')}")
                logger.info(f"Error message: {getattr(result, 'error_message', 'N/A')}")
                
                if hasattr(result, 'markdown'):
                    logger.info(f"Markdown exists: {result.markdown is not None}")
                    if result.markdown:
                        logger.info(f"Markdown length: {len(result.markdown)}")
                        logger.info(f"Markdown preview (first 200 chars): {result.markdown[:200]}")
                    else:
                        logger.warning("Markdown is None or empty!")
                else:
                    logger.warning("Result has no markdown attribute!")
                    
                if hasattr(result, 'html'):
                    logger.info(f"HTML exists: {result.html is not None}")
                    if result.html:
                        logger.info(f"HTML length: {len(result.html)}")
                    else:
                        logger.warning("HTML is None or empty!")
                else:
                    logger.warning("Result has no html attribute!")
                
                if hasattr(result, 'metadata') and result.metadata:
                    logger.info(f"Metadata: {result.metadata}")
                else:
                    logger.warning("No metadata found!")
                
                return {
                    "success": result.success,
                    "markdown": result.markdown if hasattr(result, 'markdown') and result.markdown else "",
                    "title": result.metadata.get('title', '') if hasattr(result, 'metadata') and result.metadata else "",
                    "html": result.html if hasattr(result, 'html') and result.html else "",
                    "status_code": result.status_code if hasattr(result, 'status_code') else None,
                    "error_message": result.error_message if hasattr(result, 'error_message') and not result.success else ""
                }
                
        except Exception as e:
            logger.error(f"=== CRAWL4AI ERROR for URL {url} ===")
            logger.error(f"Error: {e}")
            logger.error(f"Exception type: {type(e)}")
            import traceback
            logger.error(f"Stack trace: {traceback.format_exc()}")
            return {
                "success": False,
                "markdown": "",
                "title": "",
                "html": "",
                "status_code": None,
                "error_message": str(e)
            }