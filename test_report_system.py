#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test script for the simplified report generation system.
This script verifies that our simplified approach works correctly.
"""

import os
import sys
import logging
import subprocess
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_report_system")

def test_direct_report_generation():
    """Test the direct report generation with the simplified generator."""
    logger.info("Testing direct report generation...")
    
    # Run the simple report generator directly
    cmd = [sys.executable, "generate_report.py", "--client", "General", "--frequency", "weekly"]
    
    logger.info(f"Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        logger.info("✅ Direct report generation successful!")
        # Print the output
        for line in result.stdout.splitlines():
            if "Markdown:" in line or "HTML:" in line or "PDF:" in line:
                logger.info(f"  {line.strip()}")
        return True
    else:
        logger.error("❌ Direct report generation failed!")
        logger.error(f"Error: {result.stderr}")
        return False

def test_bridge_integration():
    """Test the bridge integration with the API server."""
    logger.info("Testing report bridge integration...")
    
    try:
        # Import the bridge module
        sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))
        from report_bridge import generate_report, list_reports
        
        # Generate a report through the bridge
        logger.info("Generating report through bridge...")
        result = generate_report(client="General", frequency="weekly")
        
        if result["success"]:
            logger.info("✅ Bridge report generation successful!")
            for report_type, path in result["paths"].items():
                logger.info(f"  {report_type.capitalize()}: {path}")
            
            # List available reports
            logger.info("Listing available reports...")
            time.sleep(1)  # Short delay to ensure file system catches up
            reports = list_reports(client="General", frequency="weekly")
            
            if reports and len(reports) > 0:
                logger.info(f"✅ Found {len(reports)} reports through bridge!")
                for i, report in enumerate(reports[:3]):  # Show first 3 reports
                    logger.info(f"  Report {i+1}: {report['title']} - {report['formatted_date']}")
                return True
            else:
                logger.error("❌ No reports found through bridge!")
                return False
        else:
            logger.error("❌ Bridge report generation failed!")
            logger.error(f"Error: {result['message']}")
            return False
            
    except ImportError as e:
        logger.error(f"❌ Bridge integration failed - import error: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Bridge integration failed - unexpected error: {e}")
        return False

def test_api_server_startup():
    """Test if the API server can start."""
    logger.info("Testing API server startup (will exit after 5 seconds)...")
    
    # Start the API server in a subprocess
    cmd = [sys.executable, "run_api_server.py"]
    
    try:
        # Start the server with a 5-second timeout
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True
        )
        
        # Wait for a few seconds to see if the server starts
        time.sleep(5)
        
        # Check if the process is still running
        if process.poll() is None:
            logger.info("✅ API server started successfully!")
            # Terminate the server
            process.terminate()
            process.wait(timeout=3)
            return True
        else:
            # Process exited, check the output
            stdout, stderr = process.communicate()
            logger.error("❌ API server failed to start!")
            logger.error(f"Stdout: {stdout}")
            logger.error(f"Stderr: {stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ API server test failed with an exception: {e}")
        # Make sure to terminate the process if it's still running
        try:
            process.terminate()
        except:
            pass
        return False

def main():
    """Run all tests in sequence."""
    logger.info("Starting report system tests...")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Test started at: {timestamp}")
    
    # Run the tests
    direct_result = test_direct_report_generation()
    bridge_result = test_bridge_integration()
    api_result = test_api_server_startup()
    
    # Print summary
    logger.info("==== Test Summary ====")
    logger.info(f"Direct report generation: {'✅ PASSED' if direct_result else '❌ FAILED'}")
    logger.info(f"Bridge integration: {'✅ PASSED' if bridge_result else '❌ FAILED'}")
    logger.info(f"API server startup: {'✅ PASSED' if api_result else '❌ FAILED'}")
    
    if direct_result and bridge_result and api_result:
        logger.info("🎉 All tests passed! The system is working correctly.")
        return 0
    else:
        logger.error("❌ Some tests failed. See logs for details.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 