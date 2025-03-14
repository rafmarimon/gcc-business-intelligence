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

def run_weekly_collection():
    """Run the weekly collection, analysis, and report generation process."""
    start_time = datetime.now()
    logger.info(f"Starting weekly collection at {start_time}")
    
    try:
        # Step 1: Collect news
        logger.info("Step 1: Collecting news from UAE/GCC sources...")
        collector = GCCBusinessNewsCollector()
        articles = collector.collect_news()
        
        if not articles:
            logger.warning("No articles collected. Stopping process.")
            return
        
        logger.info(f"Collected {len(articles)} articles")
        
        # Step 2: Analyze news and generate report
        logger.info("Step 2: Analyzing news and generating weekly report...")
        analyzer = GCCBusinessNewsAnalyzer()
        report_path, _ = analyzer.generate_weekly_report(articles)
        
        if not report_path:
            logger.warning("Failed to generate report. Stopping process.")
            return
        
        logger.info(f"Generated weekly report at {report_path}")
        
        # Step 3: Generate LinkedIn posts
        logger.info("Step 3: Generating LinkedIn posts...")
        content_generator = LinkedInContentGenerator()
        posts = content_generator.generate_linkedin_posts()
        
        logger.info(f"Generated {len(posts)} LinkedIn posts")
        
        # Log completion
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Weekly collection completed in {duration}")
        
    except Exception as e:
        logger.error(f"Error in weekly collection: {e}", exc_info=True)

def schedule_weekly_task():
    """Schedule the weekly task to run every Sunday at midnight UAE time (UTC+4)."""
    schedule.every().sunday.at("00:00").do(run_weekly_collection)
    logger.info("Scheduled weekly collection for every Sunday at 00:00 (UTC+4)")
    
    # Run immediately as well
    logger.info("Running initial collection now...")
    run_weekly_collection()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Check every hour

if __name__ == "__main__":
    logger.info("Starting GCC Business Intelligence Platform")
    schedule_weekly_task() 