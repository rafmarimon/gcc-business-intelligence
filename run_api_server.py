#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv

# Configure detailed logging to file
log_file = f"api_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
logger.info(f"Logging to {log_file}")

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
logger.info(f"Added {os.path.dirname(os.path.abspath(__file__))} to Python path")

# Print Python path for debugging
logger.info(f"Python path: {sys.path}")

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded")

def run_api_server():
    """Run the API server with proper error handling and reporting."""
    try:
        # Step-by-step imports to isolate the error
        logger.info("Step 1: Checking if src directory exists")
        src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            logger.info(f"src directory found at {src_dir}")
            # List files in the directory
            files = os.listdir(src_dir)
            logger.info(f"Files in src directory: {files}")
        else:
            logger.error(f"src directory not found at {src_dir}")
            raise ImportError("src directory not found")
        
        logger.info("Step 2: Checking if api_server.py exists")
        api_server_path = os.path.join(src_dir, 'api_server.py')
        if os.path.exists(api_server_path):
            logger.info(f"api_server.py found at {api_server_path}")
        else:
            logger.error(f"api_server.py not found at {api_server_path}")
            raise ImportError("api_server.py not found")
        
        logger.info("Step 3: Attempting to import src package")
        try:
            import src
            logger.info("Successfully imported src package")
        except ImportError as e:
            logger.error(f"Error importing src package: {e}")
            logger.error(traceback.format_exc())
            raise
        
        logger.info("Step 4: Attempting to import src.api_server module")
        try:
            import src.api_server
            logger.info("Successfully imported src.api_server module")
        except ImportError as e:
            logger.error(f"Error importing src.api_server module: {e}")
            logger.error(traceback.format_exc())
            # Try to import manually
            logger.info("Attempting manual import using exec")
            try:
                api_server_code = open(api_server_path, 'r').read()
                namespace = {}
                exec(api_server_code, namespace)
                logger.info(f"Manual import succeeded. Keys: {list(namespace.keys())}")
                if 'app' in namespace:
                    app = namespace['app']
                    logger.info("Found app in manual import")
                else:
                    logger.error("app not found in manual import")
                    raise ImportError("app not found in manual import")
            except Exception as ex:
                logger.error(f"Manual import failed: {ex}")
                logger.error(traceback.format_exc())
                raise
        
        logger.info("Step 5: Checking for app in src.api_server")
        if hasattr(src.api_server, 'app'):
            app = src.api_server.app
            logger.info("Successfully retrieved app from src.api_server")
        else:
            logger.error("app not found in src.api_server")
            logger.error(f"Available attributes: {dir(src.api_server)}")
            raise ImportError("app not found in src.api_server")
        
        # Set the port
        port = int(os.environ.get('PORT', 8080))
        
        # Log the configuration
        logger.info(f"Running the API server on port {port}")
        logger.info(f"OpenAI API key: {'Configured' if os.getenv('OPENAI_API_KEY') else 'Missing'}")
        logger.info(f"Debug mode: {os.getenv('DEBUG', 'False')}")
        
        # Run the app
        app.run(host='0.0.0.0', port=port, debug=(os.getenv('DEBUG', 'False').lower() == 'true'))
        
    except ImportError as e:
        logger.error(f"ImportError: {e}")
        logger.error("This could be due to missing modules or incorrect Python path.")
        logger.error("Please make sure all required packages are installed:")
        logger.error("  pip install -r requirements.txt")
        logger.error(traceback.format_exc())
        print(f"Error importing required modules. Make sure paths are correct. See {log_file} for details.")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error running API server: {e}")
        logger.error(traceback.format_exc())
        print(f"Error running API server. See {log_file} for details.")
        sys.exit(1)

if __name__ == "__main__":
    run_api_server() 