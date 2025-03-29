#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Auto Summarization Utility

This module provides functionality to automatically summarize articles
using OpenAI's API. It can be run as a standalone script or imported
and used within other modules.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

import openai
from dotenv import load_dotenv

from src.models.client_model import get_client_model
from src.collectors.simple_crawler import SimpleCrawler
from src.utils.file_utils import ensure_dir_exists, list_files

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Get OpenAI API key from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def get_unsummarized_articles(limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get a list of articles that don't have summaries yet.
    
    Args:
        limit: Maximum number of articles to retrieve
        
    Returns:
        List of article data dictionaries
    """
    try:
        # Initialize the crawler to access Redis
        crawler = SimpleCrawler()
        
        # Get all article IDs from Redis
        article_ids = crawler.cache.get_keys("article:*")
        
        # Filter for articles without summaries
        unsummarized_articles = []
        for article_id in article_ids:
            article_data = crawler.cache.get(article_id)
            if article_data and isinstance(article_data, dict):
                # Check if it has no summary or an empty summary
                if not article_data.get('summary'):
                    unsummarized_articles.append(article_data)
                    
                    # Stop when we hit the limit
                    if len(unsummarized_articles) >= limit:
                        break
        
        logger.info(f"Found {len(unsummarized_articles)} articles without summaries")
        return unsummarized_articles
        
    except Exception as e:
        logger.error(f"Error getting unsummarized articles: {str(e)}")
        return []

def generate_summary(article_content: str, title: str = "") -> Optional[str]:
    """
    Generate a summary for an article using OpenAI's API.
    
    Args:
        article_content: The content of the article to summarize
        title: The title of the article
        
    Returns:
        Generated summary or None if an error occurred
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not found in environment variables")
        return None
        
    try:
        # Configure the OpenAI client
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Prepare the prompt
        article_text = article_content
        if len(article_text) > 15000:
            # Truncate long content to avoid token limits
            article_text = article_text[:15000] + "..."
            
        # Build the prompt
        prompt = f"""
        Please summarize the following article in 3-4 sentences.
        Focus on the main points and key information.
        
        Title: {title}
        
        Article:
        {article_text}
        
        Summary:
        """
        
        # Make the API call
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise article summaries."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.5
        )
        
        # Extract the summary
        summary = response.choices[0].message.content.strip()
        return summary
        
    except Exception as e:
        logger.error(f"Error generating summary with OpenAI: {str(e)}")
        return None

def update_article_with_summary(article_id: str, summary: str) -> bool:
    """
    Update an article in Redis with the generated summary.
    
    Args:
        article_id: The ID of the article to update
        summary: The generated summary
        
    Returns:
        True if the update was successful, False otherwise
    """
    try:
        # Initialize the crawler to access Redis
        crawler = SimpleCrawler()
        
        # Get the current article data
        article_data = crawler.cache.get(article_id)
        if not article_data:
            logger.error(f"Article not found: {article_id}")
            return False
            
        # Update the summary
        article_data['summary'] = summary
        article_data['summary_generated_at'] = datetime.now().isoformat()
        
        # Save the updated article data
        crawler.cache.set(article_id, article_data)
        logger.info(f"Updated article with summary: {article_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating article with summary: {str(e)}")
        return False

def auto_summarize_articles(limit: int = 10) -> int:
    """
    Automatically summarize articles that don't have summaries yet.
    
    Args:
        limit: Maximum number of articles to summarize
        
    Returns:
        Number of articles successfully summarized
    """
    if not OPENAI_API_KEY:
        logger.error("OpenAI API key not found in environment variables")
        return 0
        
    try:
        logger.info("Starting auto-summarization process")
        
        # Get articles without summaries
        unsummarized_articles = get_unsummarized_articles(limit)
        
        if not unsummarized_articles:
            logger.info("No articles found that need summarization")
            return 0
            
        # Track successful summarizations
        success_count = 0
        
        # Process each article
        for article in unsummarized_articles:
            article_id = article.get('id')
            if not article_id:
                continue
                
            # Get the full Redis key
            redis_key = f"article:{article_id}"
            
            # Generate a summary
            summary = generate_summary(
                article_content=article.get('content', ''),
                title=article.get('title', '')
            )
            
            if not summary:
                logger.warning(f"Failed to generate summary for article: {article_id}")
                continue
                
            # Update the article with the summary
            if update_article_with_summary(redis_key, summary):
                success_count += 1
                
            # Rate limit API calls
            time.sleep(1)
        
        logger.info(f"Successfully summarized {success_count} articles")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in auto-summarization process: {str(e)}")
        return 0

if __name__ == "__main__":
    # When run as a script, summarize up to 20 articles
    auto_summarize_articles(20) 