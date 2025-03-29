#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LinkedIn Content Generator Module for Market Intelligence Platform.

This module generates LinkedIn-ready posts with captions, hashtags, and
optional AI-generated images based on reports and articles.
"""

import base64
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

from dotenv import load_dotenv

from src.crawler import get_crawler
from src.report_generator import get_report_generator
from src.utils.redis_cache import get_redis_cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LinkedInGenerator:
    """
    Generate LinkedIn-ready posts with captions, hashtags, and images.
    """
    
    def __init__(self):
        """Initialize the LinkedIn content generator."""
        self.redis_cache = get_redis_cache()
        self.crawler = get_crawler()
        self.report_generator = get_report_generator()
        
        # LinkedIn post tones
        self.tones = {
            "professional": "Write in a formal, educational tone with industry-specific terminology. Focus on data and insights.",
            "casual": "Write in a conversational, approachable tone. Use simple language and ask engaging questions.",
            "engaging": "Write in an enthusiastic, action-oriented tone. Use power words and compelling statements."
        }
        
        # Default settings
        self.default_tone = os.getenv("LINKEDIN_DEFAULT_TONE", "professional")
        self.use_images = os.getenv("USE_GPT4O_IMAGES", "true").lower() == "true"
        self.image_model = os.getenv("GPT4O_IMAGE_MODEL", "gpt-4o")
        
        logger.info("LinkedInGenerator initialized")
    
    def _generate_post_content(self, source_data: Dict[str, Any], tone: str) -> Tuple[Optional[str], Optional[List[str]]]:
        """Generate post caption and hashtags using LLM."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not set. Cannot generate LinkedIn post.")
            return None, None
        
        try:
            from openai import OpenAI
            
            # Determine if source is a report or article
            is_report = "content" in source_data and "client_name" in source_data
            
            if is_report:
                # For report-based posts
                client_name = source_data.get("client_name", "our client")
                report_content = source_data.get("content", "")
                
                # Truncate report for the prompt
                max_content_length = 4000
                if len(report_content) > max_content_length:
                    report_content = report_content[:max_content_length] + "..."
                
                prompt_content = f"""
                This is a market intelligence report for {client_name}:
                
                {report_content}
                """
            else:
                # For article-based posts
                title = source_data.get("title", "")
                summary = source_data.get("summary", source_data.get("description", ""))
                
                prompt_content = f"""
                Article Title: {title}
                
                Summary: {summary}
                """
            
            # Get tone instructions
            tone_instruction = self.tones.get(tone, self.tones["professional"])
            
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a professional LinkedIn content creator who specializes in business and market intelligence content. {tone_instruction}"},
                    {"role": "user", "content": f"""Create a LinkedIn post based on the following content:
                    
                    {prompt_content}
                    
                    Create a compelling LinkedIn post with:
                    1. An attention-grabbing opening line
                    2. 2-3 paragraphs highlighting key insights
                    3. A clear call-to-action
                    
                    Then, provide 5-7 relevant hashtags that would maximize visibility.
                    
                    Format your response as:
                    
                    POST:
                    [Your LinkedIn post content here]
                    
                    HASHTAGS:
                    [Your hashtags here, separated by commas]
                    """}
                ],
                max_tokens=700,
                temperature=0.7
            )
            
            result = response.choices[0].message.content.strip()
            
            # Extract post and hashtags from the result
            post_content = None
            hashtags = None
            
            if "POST:" in result and "HASHTAGS:" in result:
                parts = result.split("HASHTAGS:")
                post_content = parts[0].replace("POST:", "").strip()
                hashtags_text = parts[1].strip()
                hashtags = [tag.strip() for tag in hashtags_text.split(",")]
            else:
                post_content = result
                hashtags = []
            
            return post_content, hashtags
            
        except Exception as e:
            logger.error(f"Error generating LinkedIn post: {str(e)}")
            return None, None
    
    def _generate_image(self, source_data: Dict[str, Any]) -> Optional[str]:
        """Generate an image for the LinkedIn post using DALL-E."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not self.use_images:
            return None
        
        try:
            from openai import OpenAI
            
            # Determine if source is a report or article
            is_report = "content" in source_data and "client_name" in source_data
            
            if is_report:
                client_name = source_data.get("client_name", "a business")
                prompt = f"A professional, business-oriented image representing market intelligence data for {client_name}. Include data visualizations, business professionals, or relevant industry elements. Style: clean, corporate, professional."
            else:
                title = source_data.get("title", "")
                prompt = f"A professional, business-oriented image representing the article: '{title}'. Style: clean, modern, suitable for LinkedIn."
            
            client = OpenAI(api_key=api_key)
            response = client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            
            # Download the image and convert to base64
            import requests
            image_response = requests.get(image_url)
            if image_response.status_code == 200:
                image_data = base64.b64encode(image_response.content).decode('utf-8')
                return image_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None
    
    def generate_post_from_report(self, client_id: str, report_id: Optional[str] = None, tone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate a LinkedIn post from a client report.
        
        Args:
            client_id: The client ID
            report_id: Specific report ID or None for latest
            tone: Post tone (professional, casual, engaging)
            
        Returns:
            The generated post data or None if failed
        """
        # Get the report
        report_data = self.report_generator.get_client_report(client_id, report_id)
        if not report_data:
            logger.error(f"Cannot generate LinkedIn post - report not found for client {client_id}")
            return None
        
        # Use specified tone or default
        post_tone = tone or self.default_tone
        
        # Generate post content
        post_content, hashtags = self._generate_post_content(report_data, post_tone)
        if not post_content:
            logger.error(f"Failed to generate LinkedIn post content")
            return None
        
        # Generate image if enabled
        image_data = None
        if self.use_images:
            image_data = self._generate_image(report_data)
        
        # Create post data
        post_data = {
            "id": f"linkedin-post-{int(time.time())}",
            "type": "report",
            "source_id": report_data.get("id"),
            "client_id": client_id,
            "client_name": report_data.get("client_name"),
            "content": post_content,
            "hashtags": hashtags,
            "tone": post_tone,
            "has_image": image_data is not None,
            "generated_at": datetime.now().isoformat()
        }
        
        # Store image separately if present
        if image_data:
            image_key = f"linkedin:image:{post_data['id']}"
            self.redis_cache.set(image_key, image_data)
        
        # Store the post
        self._store_linkedin_post(post_data)
        
        logger.info(f"Generated LinkedIn post from report for client {client_id}")
        return post_data
    
    def generate_post_from_article(self, article_id: str, tone: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Generate a LinkedIn post from an article.
        
        Args:
            article_id: The article ID
            tone: Post tone (professional, casual, engaging)
            
        Returns:
            The generated post data or None if failed
        """
        # Get the article
        article_data = self.redis_cache.get(f"article:{article_id}")
        if not article_data:
            logger.error(f"Cannot generate LinkedIn post - article not found: {article_id}")
            return None
        
        # Use specified tone or default
        post_tone = tone or self.default_tone
        
        # Generate post content
        post_content, hashtags = self._generate_post_content(article_data, post_tone)
        if not post_content:
            logger.error(f"Failed to generate LinkedIn post content")
            return None
        
        # Generate image if enabled
        image_data = None
        if self.use_images:
            image_data = self._generate_image(article_data)
        
        # Create post data
        post_data = {
            "id": f"linkedin-post-{int(time.time())}",
            "type": "article",
            "source_id": article_id,
            "title": article_data.get("title"),
            "url": article_data.get("url"),
            "content": post_content,
            "hashtags": hashtags,
            "tone": post_tone,
            "has_image": image_data is not None,
            "generated_at": datetime.now().isoformat()
        }
        
        # Store image separately if present
        if image_data:
            image_key = f"linkedin:image:{post_data['id']}"
            self.redis_cache.set(image_key, image_data)
        
        # Store the post
        self._store_linkedin_post(post_data)
        
        logger.info(f"Generated LinkedIn post from article: {article_data.get('title', article_id)}")
        return post_data
    
    def _store_linkedin_post(self, post_data: Dict[str, Any]) -> bool:
        """Store a LinkedIn post in Redis."""
        try:
            post_id = post_data['id']
            
            # Store the post data
            post_key = f"linkedin:post:{post_id}"
            self.redis_cache.set(post_key, post_data)
            
            # Add to posts list
            posts_key = "linkedin:posts"
            posts = self.redis_cache.get(posts_key) or []
            posts.insert(0, post_id)
            posts = posts[:100]  # Keep only the 100 most recent
            self.redis_cache.set(posts_key, posts)
            
            # Also add to date-specific list
            date_str = datetime.now().strftime("%Y-%m-%d")
            date_key = f"linkedin:posts:{date_str}"
            date_posts = self.redis_cache.get(date_key) or []
            date_posts.insert(0, post_id)
            self.redis_cache.set(date_key, date_posts)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing LinkedIn post: {str(e)}")
            return False
    
    def get_post(self, post_id: str, include_image: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get a LinkedIn post by ID.
        
        Args:
            post_id: The post ID
            include_image: Whether to include the image data
            
        Returns:
            The post data or None if not found
        """
        try:
            post_key = f"linkedin:post:{post_id}"
            post_data = self.redis_cache.get(post_key)
            
            if not post_data:
                logger.warning(f"LinkedIn post not found: {post_id}")
                return None
            
            # Include image if requested and available
            if include_image and post_data.get("has_image"):
                image_key = f"linkedin:image:{post_id}"
                image_data = self.redis_cache.get(image_key)
                if image_data:
                    post_data["image_data"] = image_data
            
            return post_data
            
        except Exception as e:
            logger.error(f"Error retrieving LinkedIn post: {str(e)}")
            return None
    
    def get_recent_posts(self, limit: int = 10, include_images: bool = False) -> List[Dict[str, Any]]:
        """
        Get recent LinkedIn posts.
        
        Args:
            limit: Maximum number of posts to retrieve
            include_images: Whether to include image data
            
        Returns:
            List of post data
        """
        try:
            posts_key = "linkedin:posts"
            post_ids = self.redis_cache.get(posts_key) or []
            
            posts = []
            for post_id in post_ids[:limit]:
                post_data = self.get_post(post_id, include_images)
                if post_data:
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.error(f"Error retrieving recent LinkedIn posts: {str(e)}")
            return []
    
    def get_posts_by_date(self, date_str: str, include_images: bool = False) -> List[Dict[str, Any]]:
        """
        Get LinkedIn posts for a specific date.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            include_images: Whether to include image data
            
        Returns:
            List of post data
        """
        try:
            date_key = f"linkedin:posts:{date_str}"
            post_ids = self.redis_cache.get(date_key) or []
            
            posts = []
            for post_id in post_ids:
                post_data = self.get_post(post_id, include_images)
                if post_data:
                    posts.append(post_data)
            
            return posts
            
        except Exception as e:
            logger.error(f"Error retrieving LinkedIn posts for date {date_str}: {str(e)}")
            return []

# Create a singleton instance
_linkedin_generator = None

def get_linkedin_generator() -> LinkedInGenerator:
    """
    Get the singleton LinkedIn generator instance.
    
    Returns:
        The LinkedInGenerator instance
    """
    global _linkedin_generator
    if _linkedin_generator is None:
        _linkedin_generator = LinkedInGenerator()
    return _linkedin_generator 