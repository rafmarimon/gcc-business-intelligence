#!/usr/bin/env python
"""
Test script to verify OpenAI API connection and report generation capabilities.
This script tests both the primary and fallback functionality.
"""
import os
import sys
import logging
from dotenv import load_dotenv
from src.utils.openai_utils import OpenAIClient
from src.processors.news_analyzer import GCCBusinessNewsAnalyzer
from src.generators.linkedin_content import LinkedInContentGenerator
import json

# Configure logging for the test script
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("api_test")

def test_openai_connection():
    """
    Test the basic OpenAI API connection with both primary and fallback models.
    """
    logger.info("Testing OpenAI API connection...")
    client = OpenAIClient()  # Initialize with values from .env
    
    # Test basic connection
    success, message = client.verify_connection()
    if success:
        logger.info(f"✅ Connection test successful: {message}")
    else:
        logger.error(f"❌ Connection test failed: {message}")
        return False
    
    # Test primary model explicitly
    try:
        primary_model = client.primary_model
        logger.info(f"Testing primary model: {primary_model}")
        
        response = client.create_chat_completion(
            model=primary_model,
            messages=[{"role": "user", "content": "What is the capital of UAE?"}],
            max_tokens=50,
            use_fallback=False  # Disable fallback to test primary model only
        )
        
        content = response.choices[0].message.content
        logger.info(f"✅ Primary model ({primary_model}) response: {content[:50]}...")
    except Exception as e:
        logger.error(f"❌ Primary model test failed: {str(e)}")
        
    # Test fallback model
    try:
        fallback_model = client.fallback_model
        logger.info(f"Testing fallback model: {fallback_model}")
        
        response = client.create_chat_completion(
            model=fallback_model,
            messages=[{"role": "user", "content": "What is the tallest building in Dubai?"}],
            max_tokens=50
        )
        
        content = response.choices[0].message.content
        logger.info(f"✅ Fallback model ({fallback_model}) response: {content[:50]}...")
    except Exception as e:
        logger.error(f"❌ Fallback model test failed: {str(e)}")
    
    return True

def test_news_analyzer():
    """
    Test the news analyzer module with sample data.
    """
    logger.info("Testing news analyzer module...")
    analyzer = GCCBusinessNewsAnalyzer()
    
    # Create sample test data
    sample_articles = [
        {
            "headline": "UAE announces new initiative to boost tech investment",
            "summary": "The UAE government launched a $1 billion fund to support tech startups and innovation.",
            "source_name": "Gulf News",
            "country": "UAE",
            "published_at": "2023-05-01",
            "link": "https://example.com/uae-tech-fund",
            "category": "Technology"
        },
        {
            "headline": "US-UAE trade volume increases by 20% in Q1 2023",
            "summary": "Bilateral trade between the United States and UAE grew significantly in the first quarter.",
            "source_name": "Khaleej Times",
            "country": "UAE",
            "published_at": "2023-04-28",
            "link": "https://example.com/us-uae-trade",
            "category": "Trade"
        },
        {
            "headline": "New sustainability initiatives announced across GCC",
            "summary": "GCC countries revealed coordinated plans to reduce carbon emissions by 30% by 2030.",
            "source_name": "Arab News",
            "country": "Saudi Arabia",
            "published_at": "2023-04-25",
            "link": "https://example.com/gcc-sustainability",
            "category": "Environment"
        }
    ]
    
    # Save sample data to a test file
    os.makedirs("data", exist_ok=True)
    with open("data/test_news_data.json", "w") as f:
        json.dump(sample_articles, f)
    
    # Test analysis
    stats = analyzer.analyze_news(sample_articles)
    logger.info(f"✅ Analysis generated stats with {len(stats)} fields")
    
    # Test report generation
    try:
        report_path, report_text = analyzer.generate_daily_report(sample_articles)
        if report_path:
            logger.info(f"✅ Test report generated at: {report_path}")
            logger.info(f"Preview: {report_text[:100]}...")
        else:
            logger.warning("❌ Report generation returned None")
    except Exception as e:
        logger.error(f"❌ Error in report generation: {str(e)}")
    
    return True

def test_linkedin_content():
    """
    Test the LinkedIn content generator with a sample report.
    """
    logger.info("Testing LinkedIn content generator...")
    generator = LinkedInContentGenerator()
    
    # Create a sample report
    sample_report = """
    # UAE/GCC Business Intelligence Report
    
    ## Executive Summary
    The UAE economy continues to show strong growth in non-oil sectors,
    particularly in technology, finance, and tourism. Recent government
    initiatives are supporting digital transformation across industries.
    
    ## Key Trends
    - Fintech investments increased by 30% in Q1
    - UAE-US trade volume reached $25 billion
    - New sustainability initiatives announced across GCC
    """
    
    # Save sample report
    os.makedirs("reports", exist_ok=True)
    sample_report_path = "reports/test_report.md"
    with open(sample_report_path, "w") as f:
        f.write(sample_report)
    
    # Test post generation for different types
    post_types = ["general", "market_update", "sector_focus", "us_uae_relations"]
    
    for post_type in post_types:
        try:
            logger.info(f"Generating {post_type} post...")
            post = generator.generate_post(sample_report_path, post_type=post_type)
            
            if post:
                # Save the post
                file_path = generator.save_post(post, post_type)
                logger.info(f"✅ {post_type.capitalize()} post saved to: {file_path}")
                logger.info(f"Preview: {post[:100]}...")
            else:
                logger.warning(f"❌ {post_type.capitalize()} post generation returned None")
        except Exception as e:
            logger.error(f"❌ Error generating {post_type} post: {str(e)}")
    
    return True

def main():
    """Main test function"""
    logger.info("Starting API and module tests...")
    
    # Test OpenAI connection
    if not test_openai_connection():
        logger.error("OpenAI connection test failed. Exiting.")
        return 1
    
    # Test news analyzer
    test_news_analyzer()
    
    # Test LinkedIn content generator
    test_linkedin_content()
    
    logger.info("All tests completed.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 