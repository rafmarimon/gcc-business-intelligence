#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import traceback
from datetime import datetime
from dotenv import load_dotenv
import socket
import errno

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
        
        # Use port 3000 by default (less likely to conflict on macOS)
        default_port = 3000
        # Try to get port from environment variable first
        port = int(os.environ.get('PORT', default_port))
        
        # Log the configuration
        logger.info(f"Running the API server on port {port}")
        logger.info(f"OpenAI API key: {'Configured' if os.getenv('OPENAI_API_KEY') else 'Missing'}")
        logger.info(f"Debug mode: {os.getenv('DEBUG', 'False')}")
        
        # Auto retry with alternative ports if specified port is in use
        max_retries = 5  # Try more ports
        current_port = port
        
        for retry in range(max_retries + 1):
            try:
                # Run the app
                logger.info(f"Attempting to start server on port {current_port} (attempt {retry + 1}/{max_retries + 1})")
                app.run(host='0.0.0.0', port=current_port, debug=(os.getenv('DEBUG', 'False').lower() == 'true'))
                break  # If successful, break the loop
            except socket.error as e:
                # Only retry if the error is "address already in use"
                if e.errno == errno.EADDRINUSE:
                    if retry < max_retries:
                        logger.warning(f"Port {current_port} is already in use. Trying alternative port.")
                        current_port = current_port + 1  # Try next port
                    else:
                        logger.error(f"All ports from {port} to {current_port} are in use.")
                        print(f"ERROR: Could not find an available port. Tried ports {port} to {current_port}.")
                        print("Either free one of these ports or specify a different port using the PORT environment variable.")
                        print("On macOS, AirPlay Receiver commonly uses port 5000. You can disable it in System Preferences.")
                        sys.exit(1)
                else:
                    # For other socket errors, don't retry
                    logger.error(f"Socket error: {e}")
                    raise
        
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