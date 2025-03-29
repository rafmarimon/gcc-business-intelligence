#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Chatbot AI Module for Market Intelligence Platform.

This module provides AI-powered chat functionality using OpenAI.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Tuple

import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize OpenAI with API key
openai.api_key = os.getenv("OPENAI_API_KEY")

def process_chat_message(message: str, context: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]], List[str]]:
    """
    Process a chat message using OpenAI.
    
    Args:
        message: The user's message
        context: Context data including client info, reports, articles, etc.
        
    Returns:
        Tuple of (response, sources, suggested_followup_questions)
    """
    try:
        # Extract relevant client info
        client = context.get("client", {})
        client_name = client.get("name", "Unknown Client")
        client_industry = client.get("industry", "")
        client_interests = client.get("interests", [])
        
        # Get latest report content
        latest_report = context.get("latest_report", {})
        report_content = latest_report.get("content", "")
        report_date = ""
        if latest_report.get("generated_at"):
            report_date = datetime.fromisoformat(latest_report["generated_at"]).strftime("%Y-%m-%d")
        
        # Format recent articles
        recent_articles = context.get("recent_articles", [])
        articles_text = ""
        article_sources = []
        
        if recent_articles:
            articles_text = "Recent articles:\n"
            for i, article in enumerate(recent_articles[:5]):  # Limit to 5 articles for context
                articles_text += f"{i+1}. {article.get('title', 'Untitled')} - {article.get('source', 'Unknown')} ({article.get('published_date', 'Unknown date')})\n"
                if len(article.get('content', '')) > 100:
                    articles_text += f"   Summary: {article.get('content', '')[:150]}...\n\n"
                else:
                    articles_text += f"   Content: {article.get('content', '')}\n\n"
                
                # Add to sources for citation
                article_sources.append({
                    "title": article.get("title", "Article"),
                    "url": article.get("url", "")
                })
        
        # Format external data
        external_data = context.get("external_data", [])
        external_data_text = ""
        
        if external_data:
            external_data_text = "External data files:\n"
            for i, data in enumerate(external_data[:3]):  # Limit to 3 files for context
                external_data_text += f"{i+1}. {data.get('filename', 'Untitled')} (uploaded on {data.get('upload_date', 'Unknown date')})\n"
                # Include a small sample of content
                if len(data.get('content', '')) > 100:
                    external_data_text += f"   Sample: {data.get('content', '')[:150]}...\n\n"
                else:
                    external_data_text += f"   Content: {data.get('content', '')}\n\n"
        
        # Build system message
        system_message = f"""You are an AI assistant for the Market Intelligence Platform.
You are providing information about {client_name}, a company in the {client_industry} industry.
Their key interests include: {', '.join(client_interests)}.

You have access to the following information:
1. Latest intelligence report (generated on {report_date})
2. Recent news articles about the client or their interests
3. External data files uploaded by the user

When answering:
- Be concise and professional
- Cite your sources when referencing specific information
- If you don't have enough information to answer accurately, acknowledge this
- Provide relevant insights from the available data
"""

        # Prepare the messages
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": f"Here is the latest report for {client_name}:\n\n{report_content[:1500]}..." if report_content else f"No recent reports available for {client_name}."},
            {"role": "user", "content": articles_text if articles_text else "No recent articles available."},
            {"role": "user", "content": external_data_text if external_data_text else "No external data files available."},
            {"role": "user", "content": f"Question: {message}"}
        ]
        
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-4",  # or "gpt-3.5-turbo" for a more economical option
            messages=messages,
            max_tokens=800,
            temperature=0.7
        )
        
        # Extract the response text
        response_text = response.choices[0].message.content
        
        # Generate suggested follow-up questions
        followup_messages = messages.copy()
        followup_messages.append({"role": "assistant", "content": response_text})
        followup_messages.append({"role": "user", "content": "Based on my question and your response, generate 3 follow-up questions I might want to ask. Format them as a simple list of questions, with no numbering or introduction."})
        
        followup_response = openai.ChatCompletion.create(
            model="gpt-4",  # or "gpt-3.5-turbo" for a more economical option
            messages=followup_messages,
            max_tokens=150,
            temperature=0.7
        )
        
        # Extract and clean up suggested questions
        suggested_questions = followup_response.choices[0].message.content.strip().split('\n')
        suggested_questions = [q.strip() for q in suggested_questions if q.strip()]
        
        # Remove any numbering or bullets
        suggested_questions = [q.lstrip("- 1234567890.•") for q in suggested_questions]
        
        # Ensure we don't exceed 5 suggestions
        suggested_questions = suggested_questions[:5]
        
        # Determine sources to cite
        sources = []
        if report_content and "report" in response_text.lower():
            sources.append({
                "title": f"{client_name} Market Intelligence Report ({report_date})",
                "url": f"/clients/{client.get('id')}/reports/{latest_report.get('id')}"
            })
        
        # Add article sources if they're referenced
        for source in article_sources:
            if source["title"].lower() in response_text.lower() or source["url"] in response_text:
                sources.append(source)
        
        return response_text, sources, suggested_questions
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}", [], []

def generate_default_suggestions(client: Dict[str, Any]) -> List[str]:
    """
    Generate default suggestion buttons based on client info.
    
    Args:
        client: Client data
        
    Returns:
        List of suggested questions
    """
    suggestions = [
        "Summarize the latest report",
        "What are the main competitors in this industry?",
        f"What are the key trends for {client.get('name')}?"
    ]
    
    # Add industry-specific suggestions
    industry = client.get("industry", "").lower()
    if industry:
        if "tech" in industry or "technology" in industry:
            suggestions.append("What are the latest tech innovations in this space?")
        elif "finance" in industry or "banking" in industry:
            suggestions.append("What are the key financial metrics to watch?")
        elif "health" in industry or "medical" in industry:
            suggestions.append("What are the latest healthcare regulations affecting this client?")
        else:
            suggestions.append(f"What are the major challenges in the {industry} industry?")
    
    # Add interest-based suggestions
    interests = client.get("interests", [])
    if interests and len(interests) > 0:
        suggestions.append(f"Tell me about trends in {interests[0]}")
    
    return suggestions[:5]  # Limit to 5 suggestions 