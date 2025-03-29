#!/usr/bin/env python3
"""
Global Possibilities - UAE/GCC Business Intelligence Platform
LinkedIn Content Scheduler

This script sets up automated generation of LinkedIn content for the 
GCC Business Intelligence Platform on a daily, weekly, and monthly schedule.
"""

import os
import sys
import time
import logging
import schedule
import json
from datetime import datetime
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from src.collectors.news_collector import GCCBusinessNewsCollector
from src.generators.linkedin_content import LinkedInContentGenerator
from src.utils.redis_cache import RedisCache

# Load environment variables
load_dotenv()

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f'linkedin_scheduler_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("linkedin_scheduler")

# Set up cache
try:
    cache = RedisCache()
    logger.info("Redis cache initialized")
except Exception as e:
    logger.warning(f"Could not initialize Redis cache: {e}")
    cache = None

# Flag to control the scheduler loop
running = True

def generate_daily_content():
    """Generate daily LinkedIn content."""
    logger.info("Starting daily LinkedIn content generation")
    
    start_time = datetime.now()
    
    try:
        # Initialize LinkedIn content generator
        linkedin_generator = LinkedInContentGenerator(
            output_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin'),
            config_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'linkedin_config.json'),
            model="gpt-4o"
        )
        
        # Generate the posts
        result = linkedin_generator.generate_linkedin_posts()
        
        if not result:
            logger.error("Failed to generate LinkedIn content")
            return False
            
        # Cache the result
        if cache:
            cache.set(
                f"linkedin_daily_{datetime.now().strftime('%Y%m%d')}",
                json.dumps({
                    "posts": [
                        {
                            "text": post.get("text", ""),
                            "image_path": post.get("image_path", ""),
                            "timestamp": datetime.now().isoformat()
                        } 
                        for post in result.get("posts", [])
                    ],
                    "markdown_path": result.get("markdown_path", ""),
                    "generated_at": datetime.now().isoformat()
                }),
                expire=86400 * 7  # Cache for 7 days
            )
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Daily LinkedIn content generation completed in {duration}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating daily LinkedIn content: {e}", exc_info=True)
        return False

def generate_weekly_review():
    """Generate weekly review LinkedIn content."""
    logger.info("Starting weekly LinkedIn content generation")
    
    start_time = datetime.now()
    
    try:
        # Get the news from the past week
        news_collector = GCCBusinessNewsCollector()
        news_data = news_collector.collect_news(days=7, limit=20)
        
        # Extract the text content from the news
        news_text = "# Weekly GCC Business Review\n\n"
        
        if not news_data:
            logger.warning("No news data collected for weekly review")
            news_text += "No significant news events this week."
        else:
            # Process the collected news
            for source_name, articles in news_data.items():
                if articles:
                    news_text += f"## {source_name}\n\n"
                    for article in articles[:5]:  # Take top 5 from each source
                        news_text += f"### {article.get('title', 'Untitled')}\n\n"
                        news_text += f"{article.get('description', article.get('summary', 'No description available'))}\n\n"
                        news_text += f"Source: {article.get('source_url', 'Unknown')}\n\n"
        
        # Initialize LinkedIn content generator with weekly focus
        linkedin_generator = LinkedInContentGenerator(
            output_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin', 'weekly'),
            config_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'linkedin_config.json'),
            model="gpt-4o"
        )
        
        # Generate a single comprehensive "Week in Review" post
        post = linkedin_generator._generate_post_from_text(news_text, "week_in_review")
        
        if not post:
            logger.error("Failed to generate weekly LinkedIn content")
            return False
            
        # Save the post
        post_path = linkedin_generator.save_post(post, "week_in_review")
        
        # Cache the result
        if cache:
            cache.set(
                f"linkedin_weekly_{datetime.now().strftime('%Y%m%d')}",
                json.dumps({
                    "post": {
                        "text": post.get("text", ""),
                        "image_path": post.get("image_path", ""),
                        "timestamp": datetime.now().isoformat()
                    },
                    "post_path": post_path,
                    "generated_at": datetime.now().isoformat()
                }),
                expire=86400 * 30  # Cache for 30 days
            )
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Weekly LinkedIn content generation completed in {duration}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating weekly LinkedIn content: {e}", exc_info=True)
        return False

def generate_monthly_review():
    """Generate monthly review LinkedIn content."""
    logger.info("Starting monthly LinkedIn content generation")
    
    start_time = datetime.now()
    
    try:
        # Get the news from the past month
        news_collector = GCCBusinessNewsCollector()
        news_data = news_collector.collect_news(days=30, limit=30)
        
        # Extract the text content from the news
        news_text = "# Monthly GCC Business Review\n\n"
        
        if not news_data:
            logger.warning("No news data collected for monthly review")
            news_text += "No significant news events this month."
        else:
            # Process the collected news
            for source_name, articles in news_data.items():
                if articles:
                    news_text += f"## {source_name}\n\n"
                    for article in articles[:5]:  # Take top 5 from each source
                        news_text += f"### {article.get('title', 'Untitled')}\n\n"
                        news_text += f"{article.get('description', article.get('summary', 'No description available'))}\n\n"
                        news_text += f"Source: {article.get('source_url', 'Unknown')}\n\n"
        
        # Initialize LinkedIn content generator with monthly focus
        linkedin_generator = LinkedInContentGenerator(
            output_dir=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin', 'monthly'),
            config_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'linkedin_config.json'),
            model="gpt-4o"
        )
        
        # Generate a single comprehensive "Month in Review" post
        post = linkedin_generator._generate_post_from_text(news_text, "month_in_review")
        
        if not post:
            logger.error("Failed to generate monthly LinkedIn content")
            return False
            
        # Save the post
        post_path = linkedin_generator.save_post(post, "month_in_review")
        
        # Cache the result
        if cache:
            cache.set(
                f"linkedin_monthly_{datetime.now().strftime('%Y%m')}",
                json.dumps({
                    "post": {
                        "text": post.get("text", ""),
                        "image_path": post.get("image_path", ""),
                        "timestamp": datetime.now().isoformat()
                    },
                    "post_path": post_path,
                    "generated_at": datetime.now().isoformat()
                }),
                expire=86400 * 90  # Cache for 90 days
            )
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Monthly LinkedIn content generation completed in {duration}")
        return True
        
    except Exception as e:
        logger.error(f"Error generating monthly LinkedIn content: {e}", exc_info=True)
        return False

def setup_schedule():
    """Set up the scheduling of content generation tasks."""
    # Get schedule times from environment or use defaults
    daily_time = os.getenv('LINKEDIN_DAILY_TIME', '08:00')  # Default: 8 AM
    weekly_day = os.getenv('LINKEDIN_WEEKLY_DAY', 'monday')  # Default: Monday
    weekly_time = os.getenv('LINKEDIN_WEEKLY_TIME', '09:00')  # Default: 9 AM
    monthly_day = int(os.getenv('LINKEDIN_MONTHLY_DAY', '1'))  # Default: 1st day of month
    monthly_time = os.getenv('LINKEDIN_MONTHLY_TIME', '10:00')  # Default: A0 AM
    
    # Schedule daily generation
    logger.info(f"Scheduling daily LinkedIn content generation at {daily_time}")
    schedule.every().day.at(daily_time).do(generate_daily_content)
    
    # Schedule weekly generation
    logger.info(f"Scheduling weekly LinkedIn content generation on {weekly_day} at {weekly_time}")
    if weekly_day.lower() == 'monday':
        schedule.every().monday.at(weekly_time).do(generate_weekly_review)
    elif weekly_day.lower() == 'tuesday':
        schedule.every().tuesday.at(weekly_time).do(generate_weekly_review)
    elif weekly_day.lower() == 'wednesday':
        schedule.every().wednesday.at(weekly_time).do(generate_weekly_review)
    elif weekly_day.lower() == 'thursday':
        schedule.every().thursday.at(weekly_time).do(generate_weekly_review)
    elif weekly_day.lower() == 'friday':
        schedule.every().friday.at(weekly_time).do(generate_weekly_review)
    elif weekly_day.lower() == 'saturday':
        schedule.every().saturday.at(weekly_time).do(generate_weekly_review)
    elif weekly_day.lower() == 'sunday':
        schedule.every().sunday.at(weekly_time).do(generate_weekly_review)
    
    # Schedule monthly generation (run on a specific day of the month)
    logger.info(f"Scheduling monthly LinkedIn content generation on day {monthly_day} at {monthly_time}")
    
    def monthly_task():
        # Only run on the specified day of the month
        if datetime.now().day == monthly_day:
            return generate_monthly_review()
        return None
    
    # Check daily if it's time for the monthly task
    schedule.every().day.at(monthly_time).do(monthly_task)
    
    # Also run tests now if specified
    if os.getenv('LINKEDIN_RUN_IMMEDIATELY', 'false').lower() == 'true':
        logger.info("Running initial content generation now...")
        generate_daily_content()

def main():
    """Set up and run the LinkedIn content scheduler."""
    print("\n" + "="*80)
    print(" "*20 + "Global Possibilities - LinkedIn Content Scheduler" + " "*20)
    print("="*80 + "\n")
    
    # Create necessary directories
    content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin')
    os.makedirs(content_dir, exist_ok=True)
    os.makedirs(os.path.join(content_dir, 'weekly'), exist_ok=True)
    os.makedirs(os.path.join(content_dir, 'monthly'), exist_ok=True)
    
    # Set up the schedules
    setup_schedule()
    logger.info(f"Scheduler started. Next job will run at {schedule.next_run()}")
    print(f"Scheduler is running. Next job at {schedule.next_run()}")
    
    # Loop until interrupted
    global running
    while running:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main() 