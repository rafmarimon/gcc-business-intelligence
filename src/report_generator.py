#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Generator Module for Market Intelligence Platform.

This module generates client-specific reports using LLM based on client interests
and recently crawled articles.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv

from src.crawler import get_crawler
from src.models.client_model import get_client_model
from src.utils.redis_cache import get_redis_cache

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generate client-specific reports based on crawled articles and client interests.
    """
    
    def __init__(self):
        """Initialize the report generator."""
        self.redis_cache = get_redis_cache()
        self.crawler = get_crawler()
        self.client_model = get_client_model()
        
        # Default templates for report generation
        self.report_templates = {
            "default": """
            # Market Intelligence Report
            
            ## Summary
            {summary}
            
            ## Recent Articles
            {articles}
            
            ## Topics of Interest
            {topics}
            
            Generated on: {date}
            """
        }
        
        logger.info("ReportGenerator initialized")
    
    def _format_articles_for_report(self, articles: List[Dict[str, Any]]) -> str:
        """Format articles for inclusion in a report."""
        if not articles:
            return "No recent articles found."
        
        formatted = ""
        for i, article in enumerate(articles[:10]):  # Limit to 10 articles
            title = article.get('title', 'Untitled')
            url = article.get('url', '#')
            description = article.get('summary', article.get('description', 'No description available.'))
            
            formatted += f"### {i+1}. {title}\n\n"
            formatted += f"{description}\n\n"
            formatted += f"[Read more]({url})\n\n"
            
            # Add a separator between articles
            if i < len(articles) - 1:
                formatted += "---\n\n"
        
        return formatted
    
    def _generate_report_with_llm(self, client: Dict[str, Any], articles: List[Dict[str, Any]]) -> Optional[str]:
        """Generate a report using LLM based on client interests and articles."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not set. Cannot generate report.")
            return None
        
        try:
            from openai import OpenAI
            
            # Extract client information
            client_name = client.get('name', 'Client')
            interests = client.get('interests', [])
            industry = client.get('industry', 'General')
            
            # Prepare article data for the LLM
            article_data = ""
            for i, article in enumerate(articles[:15]):  # Limit to 15 articles
                title = article.get('title', 'Untitled')
                summary = article.get('summary', article.get('description', 'No description available.'))
                article_data += f"Article {i+1}: {title}\nSummary: {summary}\n\n"
            
            # Prepare the prompt based on client interests
            interests_text = ', '.join(interests) if interests else 'general market trends'
            
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4-turbo",  # Using a more powerful model for detailed reports
                messages=[
                    {"role": "system", "content": f"You are an expert market intelligence analyst specializing in {industry}. Your task is to generate a comprehensive market intelligence report for {client_name}, who is interested in {interests_text}. Be concise, data-driven, and focus on actionable insights."},
                    {"role": "user", "content": f"""Based on the following recent articles, generate a market intelligence report for {client_name} focused on their interests in {interests_text}.
                    
                    RECENT ARTICLES:
                    {article_data}
                    
                    Please structure the report with the following sections:
                    1. Executive Summary (2-3 paragraphs overview)
                    2. Key Market Trends (3-5 bullet points)
                    3. Industry Insights (focused on {industry})
                    4. Opportunities and Recommendations (specific to {interests_text})
                    5. Notable Recent Developments (highlight 2-3 most important news items)
                    
                    Use markdown formatting for the report structure.
                    """}
                ],
                max_tokens=1500,
                temperature=0.4
            )
            
            report_content = response.choices[0].message.content.strip()
            return report_content
            
        except Exception as e:
            logger.error(f"Error generating report with LLM: {str(e)}")
            return None
    
    def generate_client_report(self, client_id: str, force_crawl: bool = False) -> Optional[Dict[str, Any]]:
        """
        Generate a report for a specific client.
        
        Args:
            client_id: The client ID to generate report for
            force_crawl: Whether to force a fresh crawl before generating the report
            
        Returns:
            The generated report data or None if failed
        """
        # Get client data
        client = self.client_model.get_client(client_id)
        if not client:
            logger.error(f"Cannot generate report - client not found: {client_id}")
            return None
        
        # Crawl if requested
        if force_crawl:
            logger.info(f"Forcing crawl for client {client_id} before report generation")
            self.crawler.crawl_sources_for_client(client_id)
        
        # Get recent articles for this client
        articles = self.crawler.get_client_articles(client_id, limit=15)
        
        if not articles:
            logger.warning(f"No articles found for client {client_id}")
            report_data = {
                "id": f"report-{int(time.time())}",
                "client_id": client_id,
                "client_name": client.get('name', 'Unknown'),
                "generated_at": datetime.now().isoformat(),
                "content": "# No Recent Data Available\n\nThere are no recent articles available for analysis. Please try again after crawling some sources.",
                "articles_count": 0,
                "status": "empty"
            }
        else:
            # Generate report content
            report_content = self._generate_report_with_llm(client, articles)
            
            if not report_content:
                # Fallback to template-based report if LLM fails
                articles_formatted = self._format_articles_for_report(articles)
                interests = ', '.join(client.get('interests', [])) or 'General market intelligence'
                
                report_content = self.report_templates["default"].format(
                    summary=f"This report was automatically generated for {client.get('name', 'Client')}.",
                    articles=articles_formatted,
                    topics=f"Topics of Interest: {interests}",
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            
            # Create report data
            report_data = {
                "id": f"report-{int(time.time())}",
                "client_id": client_id,
                "client_name": client.get('name', 'Unknown'),
                "generated_at": datetime.now().isoformat(),
                "content": report_content,
                "articles_count": len(articles),
                "articles_ids": [a.get('id') for a in articles],
                "status": "generated"
            }
        
        # Store the report
        self._store_client_report(client_id, report_data)
        
        logger.info(f"Generated report for client {client_id}")
        return report_data
    
    def _store_client_report(self, client_id: str, report_data: Dict[str, Any]) -> bool:
        """Store a report for a client in Redis."""
        try:
            report_id = report_data['id']
            
            # Store the report data
            report_key = f"report:{report_id}"
            self.redis_cache.set(report_key, report_data)
            
            # Update latest report for this client
            latest_report_key = f"client:{client_id}:latest_report"
            self.redis_cache.set(latest_report_key, report_id)
            
            # Add to report history
            history_key = f"client:{client_id}:report_history"
            history = self.redis_cache.get(history_key) or []
            history.insert(0, report_id)
            history = history[:20]  # Keep only 20 most recent reports
            self.redis_cache.set(history_key, history)
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing report for client {client_id}: {str(e)}")
            return False
    
    def get_client_report(self, client_id: str, report_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a report for a client.
        
        Args:
            client_id: The client ID
            report_id: Specific report ID or None for latest
            
        Returns:
            The report data or None if not found
        """
        try:
            # If no specific report ID is provided, get the latest
            if not report_id:
                latest_report_key = f"client:{client_id}:latest_report"
                report_id = self.redis_cache.get(latest_report_key)
                
                if not report_id:
                    logger.warning(f"No latest report found for client {client_id}")
                    return None
            
            # Get the report data
            report_key = f"report:{report_id}"
            report_data = self.redis_cache.get(report_key)
            
            if not report_data:
                logger.warning(f"Report not found: {report_id}")
                return None
            
            return report_data
            
        except Exception as e:
            logger.error(f"Error retrieving report: {str(e)}")
            return None
    
    def get_client_report_history(self, client_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get report history for a client.
        
        Args:
            client_id: The client ID
            limit: Maximum number of reports to retrieve
            
        Returns:
            List of report data
        """
        try:
            # Get report history
            history_key = f"client:{client_id}:report_history"
            history = self.redis_cache.get(history_key) or []
            
            # Get report data for each ID
            reports = []
            for report_id in history[:limit]:
                report_data = self.redis_cache.get(f"report:{report_id}")
                if report_data:
                    reports.append(report_data)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error retrieving report history: {str(e)}")
            return []
    
    def generate_reports_for_all_clients(self) -> List[Dict[str, Any]]:
        """
        Generate reports for all clients.
        
        Returns:
            List of generated report data
        """
        clients = self.client_model.get_all_clients()
        
        logger.info(f"Generating reports for {len(clients)} clients")
        
        reports = []
        for client in clients:
            client_id = client.get('id')
            try:
                report_data = self.generate_client_report(client_id)
                if report_data:
                    reports.append(report_data)
            except Exception as e:
                logger.error(f"Error generating report for client {client_id}: {str(e)}")
        
        logger.info(f"Generated {len(reports)} reports")
        return reports

    def generate_report_from_external_data(self, client_id: str, content: str, filename: str, metadata: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Generate a report from external data.
        
        Args:
            client_id: The client ID
            content: The text content of the file
            filename: The original filename
            metadata: Optional metadata about the file
            
        Returns:
            Generated report data or None if failed
        """
        client = self.client_model.get_client(client_id)
        if not client:
            logger.error(f"Cannot generate report - client not found: {client_id}")
            return None
        
        try:
            # Get client information
            client_name = client.get("name", "Unknown Client")
            client_industry = client.get("industry", "")
            client_interests = client.get("interests", [])
            
            # Generate a report ID
            report_id = f"report-{int(time.time())}"
            
            # Prepare prompt for the LLM
            prompt = f"""Generate a comprehensive market intelligence report for {client_name}, a company in the {client_industry} industry.
Their key interests include: {', '.join(client_interests)}.

The report should be based on the following external data file: {filename}

Here is the content from the file:
{content[:3000]}  # Limit to 3000 characters to avoid token limits

Generate a professional, well-structured report with the following sections:
1. Executive Summary
2. Key Insights
3. Detailed Analysis
4. Recommendations
5. Conclusion

Format the report in Markdown."""

            # Call the OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4",  # or "gpt-3.5-turbo" for a more economical option
                messages=[
                    {"role": "system", "content": "You are an expert market intelligence analyst, creating detailed reports based on provided data."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2500,
                temperature=0.7
            )
            
            # Extract the report content
            report_content = response.choices[0].message.content
            
            # Create the report data
            timestamp = datetime.now().isoformat()
            report_data = {
                "id": report_id,
                "client_id": client_id,
                "generated_at": timestamp,
                "content": report_content,
                "source_type": "external_data",
                "source_filename": filename,
                "source_metadata": metadata or {}
            }
            
            # Store the report
            self._store_client_report(client_id, report_data)
            
            logger.info(f"Generated report from external data for client {client_name} (ID: {client_id})")
            return report_data
            
        except Exception as e:
            logger.error(f"Error generating report from external data for client {client_id}: {str(e)}")
            return None

# Create a singleton instance
_report_generator = None

def get_report_generator() -> ReportGenerator:
    """
    Get the singleton report generator instance.
    
    Returns:
        The ReportGenerator instance
    """
    global _report_generator
    if _report_generator is None:
        _report_generator = ReportGenerator()
    return _report_generator 