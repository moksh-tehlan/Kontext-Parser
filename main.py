import logging
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.config.settings import get_config
from src.repositories.sqs_repository import SQSRepository
from src.services.document_service import MockDocumentService
from src.services.s3_service import S3Service
from src.use_cases.message_processor import MessageProcessor


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('kontext_processor.log')
        ]
    )


def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config = get_config()
        logger.info("Configuration loaded successfully")
        
        # Initialize dependencies
        sqs_repository = SQSRepository(config)
        document_service = MockDocumentService()
        s3_service = S3Service(config)
        
        # Initialize message processor
        processor = MessageProcessor(
            config=config,
            sqs_repository=sqs_repository,
            document_service=document_service,
            s3_service=s3_service
        )
        
        # Start processing
        logger.info("Starting Kontext Processor...")
        processor.run_continuously()
        
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
    except Exception as e:
        logger.critical(f"Critical error in main application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()