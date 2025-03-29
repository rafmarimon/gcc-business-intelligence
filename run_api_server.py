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
        # Add more detailed path inspection for debugging
        logger.info(f"Current working directory: {os.getcwd()}")
        src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
        logger.info(f"src directory: {src_dir}")

        # Forcibly add src directory to sys.path for reliable imports
        if src_dir not in sys.path:
            sys.path.insert(0, src_dir)
            logger.info(f"Added {src_dir} to sys.path for reliable imports")

        # Directly try to import api_server and get the app
        try:
            # Import using importlib for better error handling
            import importlib.util
            api_server_path = os.path.join(src_dir, 'api_server.py')
            
            if not os.path.exists(api_server_path):
                logger.error(f"api_server.py not found at {api_server_path}")
                raise ImportError(f"api_server.py not found at {api_server_path}")
                
            logger.info(f"Loading api_server from {api_server_path}")
            
            spec = importlib.util.spec_from_file_location("api_server", api_server_path)
            if not spec:
                logger.error("Failed to create spec from file location")
                raise ImportError("Failed to create spec from file location")
                
            api_server = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(api_server)
            
            if not hasattr(api_server, 'app'):
                logger.error("app not found in api_server module")
                raise ImportError("app not found in api_server module")
                
            app = api_server.app
            logger.info("Successfully loaded Flask app from api_server.py")
            
        except ImportError as ie:
            logger.error(f"ImportError: {ie}")
            logger.error(traceback.format_exc())
            print(f"Error importing api_server. Make sure paths are correct. See {log_file} for details.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error loading api_server: {e}")
            logger.error(traceback.format_exc())
            print(f"Unexpected error loading api_server. See {log_file} for details.")
            sys.exit(1)
        
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