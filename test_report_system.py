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
    logger.info("Testing API server startup (will exit after successful detection)...")
    
    # Start the API server in a subprocess
    # Force a high port number (9000-9005) that's less likely to be in use
    os.environ['PORT'] = str(9000)
    cmd = [sys.executable, "run_api_server.py"]
    
    try:
        # Start the server process
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            env=os.environ  # Pass current environment with PORT set
        )
        
        # Wait for the server to start - up to 15 seconds
        max_wait = 15  # seconds
        start_time = time.time()
        server_started = False
        
        while time.time() - start_time < max_wait:
            if process.poll() is not None:
                # Process exited early
                stdout, stderr = process.communicate()
                
                # Check if it started successfully before exiting
                if "Running on" in stdout or "Running on" in stderr:
                    logger.info("✅ API server started successfully but exited!")
                    return True
                    
                logger.error("❌ API server failed to start and exited!")
                logger.error(f"Stdout: {stdout}")
                logger.error(f"Stderr: {stderr}")
                return False
            
            # Check if server is responding by reading partial output
            try:
                # Use select to check if there's any output to read
                import select
                readable, _, _ = select.select([process.stdout, process.stderr], [], [], 0.1)
                
                partial_output = ""
                for stream in readable:
                    # Read available output without blocking
                    line = stream.readline()
                    partial_output += line
                
                if "Running on" in partial_output:
                    logger.info("✅ API server started successfully!")
                    logger.info(f"Port detected in output: {partial_output}")
                    server_started = True
                    break
                    
            except Exception as e:
                logger.debug(f"Error checking server output: {e}")
                
            # Short sleep to reduce CPU usage
            time.sleep(0.5)
        
        # Final check - if we got here and server_started is True, consider it successful
        if server_started:
            # Terminate the server
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
            return True
            
        # If we get here, the server didn't start in time
        logger.error("❌ API server failed to start within timeout period!")
        # Capture any output we have
        try:
            stdout, stderr = process.communicate(timeout=1)
            logger.error(f"Stdout: {stdout}")
            logger.error(f"Stderr: {stderr}")
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            
        return False
            
    except Exception as e:
        logger.error(f"❌ API server test failed with an exception: {e}")
        # Make sure to terminate the process if it's still running
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
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