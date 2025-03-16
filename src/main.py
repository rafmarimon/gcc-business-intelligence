import os
import time
import schedule
from datetime import datetime
import logging
from dotenv import load_dotenv

# Import our modules
from collectors.news_collector import GCCBusinessNewsCollector
from processors.news_analyzer import GCCBusinessNewsAnalyzer
from generators.linkedin_content import LinkedInContentGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("gcc_business_intel.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("GCC_Business_Intel")

def run_daily_collection():
    """Run the daily collection, analysis, and report generation process."""
    start_time = datetime.now()
    logger.info(f"Starting daily collection at {start_time}")
    
    try:
        # Step 1: Collect news
        collector = GCCBusinessNewsCollector()
        news_data = collector.collect_news()
        
        # Step 2: Analyze news and generate report
        analyzer = GCCBusinessNewsAnalyzer()
        report_path, report_content = analyzer.generate_daily_report(news_data)
        
        # Step 3: Generate LinkedIn content
        linkedin_generator = LinkedInContentGenerator()
        linkedin_posts = linkedin_generator.generate_linkedin_posts()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Daily collection completed in {duration}")
        
        return report_path
    except Exception as e:
        logger.error(f"Error in daily collection process: {e}")
        return None

def schedule_daily_task():
    """Schedule the daily task to run every day at midnight UAE time (UTC+4)."""
    schedule.every().day.at("00:00").do(run_daily_collection)
    logger.info("Scheduled daily collection for every day at 00:00 (UTC+4)")
    
    # Run immediately as well
    logger.info("Running initial collection now...")
    run_daily_collection()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    schedule_daily_task() 