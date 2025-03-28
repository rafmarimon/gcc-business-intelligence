#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

def run_server():
    """Run the simple server that just serves reports."""
    try:
        # Import the simple server
        from src.simple_server import app
        
        # Set the port
        port = int(os.environ.get('PORT', 8080))
        
        # Log the configuration
        logger.info(f"Running the simple server on port {port}")
        
        # Run the app
        app.run(host='0.0.0.0', port=port, debug=True)
        
    except ImportError as e:
        logger.error(f"ImportError: {e}")
        logger.error("This could be due to missing modules or incorrect Python path.")
        logger.error("Please make sure all required packages are installed:")
        logger.error("  pip install -r requirements.txt")
        sys.exit(1)
    
    except Exception as e:
        logger.error(f"Error running server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_server() 