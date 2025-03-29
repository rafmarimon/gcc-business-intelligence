#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Routes for the Market Intelligence Platform

This module provides Flask API routes for accessing platform features,
including recent reports, LinkedIn content, and analytics data.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from flask import Flask, jsonify, request, send_from_directory

from src.generators.linkedin_generator import get_linkedin_generator
from src.generators.report_generator import get_report_generator
from src.models.client_model import get_client_model
from src.utils.file_utils import ensure_dir_exists, get_file_content, list_files
from src.collectors.simple_crawler import get_crawler

# Configure logging
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/api/linkedin/posts', methods=['GET'])
def get_linkedin_posts():
    """
    Get a list of generated LinkedIn posts.
    
    Query parameters:
    - client_id: Filter posts by client ID
    - count: Maximum number of posts to return (default: 10)
    - post_type: Filter by post type (general, thought_leadership, news_summary)
    
    Returns:
        JSON response with LinkedIn posts
    """
    try:
        # Get query parameters
        client_id = request.args.get('client_id')
        count = int(request.args.get('count', 10))
        post_type = request.args.get('post_type')
        
        # Initialize LinkedIn generator
        linkedin_generator = get_linkedin_generator()
        output_dir = linkedin_generator.output_dir
        
        # Ensure directory exists
        if not os.path.exists(output_dir):
            return jsonify({
                "success": False,
                "message": "LinkedIn content directory not found",
                "posts": []
            })
        
        # Get a list of JSON files in the output directory
        json_files = list_files(output_dir, pattern="*.json")
        
        # Load posts from files
        posts = []
        for file_path in json_files:
            try:
                content = get_file_content(file_path)
                post_data = json.loads(content)
                
                # Apply filters
                if client_id and post_data.get('client_id') != client_id:
                    continue
                    
                if post_type and post_data.get('post_type') != post_type:
                    continue
                
                # Add file path and filename
                post_data['file_path'] = file_path
                post_data['filename'] = os.path.basename(file_path)
                
                posts.append(post_data)
                
                # Stop when we have enough posts
                if len(posts) >= count:
                    break
            except Exception as e:
                logger.error(f"Error loading post from {file_path}: {str(e)}")
        
        # Sort posts by generation date (newest first)
        posts.sort(key=lambda x: x.get('generated_at', ''), reverse=True)
        
        return jsonify({
            "success": True,
            "count": len(posts),
            "posts": posts
        })
        
    except Exception as e:
        logger.error(f"Error getting LinkedIn posts: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "posts": []
        })

@app.route('/api/linkedin/generate', methods=['POST'])
def generate_linkedin_post():
    """
    Generate a new LinkedIn post.
    
    Expected JSON body:
    - client_id: Client ID to generate for
    - post_type: Type of post to generate
    
    Returns:
        JSON response with the generated post data
    """
    try:
        # Get JSON body
        body = request.get_json()
        client_id = body.get('client_id')
        post_type = body.get('post_type', 'general')
        
        if not client_id:
            return jsonify({
                "success": False,
                "message": "Client ID is required"
            })
        
        # Check if client exists
        client_model = get_client_model()
        client = client_model.get_client(client_id)
        if not client:
            return jsonify({
                "success": False,
                "message": f"Client not found: {client_id}"
            })
        
        # Generate the post
        linkedin_generator = get_linkedin_generator()
        post_data = linkedin_generator.generate_post(
            client_id=client_id,
            post_type=post_type,
            save_to_file=True
        )
        
        # Return the post data
        return jsonify({
            "success": True,
            "message": "LinkedIn post generated successfully",
            "post": post_data
        })
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn post: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route('/api/dashboard/analytics', methods=['GET'])
def get_dashboard_analytics():
    """
    Get analytics data for the dashboard.
    
    Returns:
        JSON response with analytics data
    """
    try:
        # Initialize components
        report_generator = get_report_generator()
        linkedin_generator = get_linkedin_generator()
        client_model = get_client_model()
        
        # Get clients
        clients = client_model.get_all_clients()
        
        # Get recent reports
        reports_dir = report_generator.reports_dir
        report_files = list_files(reports_dir, pattern="*.md") + list_files(reports_dir, pattern="*.json")
        
        # Get LinkedIn posts
        linkedin_dir = linkedin_generator.output_dir
        linkedin_files = list_files(linkedin_dir, pattern="*.json")
        
        # Compile analytics data
        analytics = {
            "clients_count": len(clients),
            "reports_count": len(report_files),
            "linkedin_posts_count": len(linkedin_files),
            "last_updated": datetime.now().isoformat()
        }
        
        return jsonify({
            "success": True,
            "analytics": analytics
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard analytics: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "analytics": {}
        })

@app.route('/api/articles', methods=['GET'])
def get_articles():
    """
    Get a list of articles.
    
    Query parameters:
    - client_id: Filter articles by client ID (via tags)
    - tag: Filter articles by tag
    - keyword: Filter articles by keyword
    - page: Page number for pagination (default: 1)
    - limit: Maximum number of articles per page (default: 10)
    
    Returns:
        JSON response with articles
    """
    try:
        # Get query parameters
        client_id = request.args.get('client_id')
        tag = request.args.get('tag')
        keyword = request.args.get('keyword')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 10))
        
        # Initialize the crawler to access Redis
        crawler = get_crawler()
        client_model = get_client_model()
        
        # Resolve client tags if client_id is provided
        client_tags = []
        if client_id:
            client = client_model.get_client(client_id)
            if client:
                client_tags = client.get('interests', [])
        
        # Get article IDs based on filters
        article_ids = []
        
        if client_tags:
            # Get articles for each tag associated with the client
            for tag in client_tags:
                tag_key = f"tag:{tag.lower()}"
                tag_article_ids = crawler.cache.get(tag_key) or []
                article_ids.extend(tag_article_ids)
            # Remove duplicates
            article_ids = list(set(article_ids))
        elif tag:
            # Get articles for specific tag
            tag_key = f"tag:{tag.lower()}"
            article_ids = crawler.cache.get(tag_key) or []
        elif keyword:
            # Get articles for specific keyword
            keyword_key = f"keyword:{keyword.lower()}"
            article_ids = crawler.cache.get(keyword_key) or []
        else:
            # Get recent articles
            article_ids = crawler.cache.get("recent_articles") or []
        
        # Paginate the results
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        paginated_ids = article_ids[start_idx:end_idx]
        
        # Load article data
        articles = []
        for article_id in paginated_ids:
            article_data = crawler.cache.get(f"article:{article_id}")
            if article_data:
                articles.append(article_data)
        
        return jsonify({
            "success": True,
            "count": len(articles),
            "total": len(article_ids),
            "page": page,
            "pages": (len(article_ids) // limit) + (1 if len(article_ids) % limit > 0 else 0),
            "has_more": end_idx < len(article_ids),
            "articles": articles
        })
        
    except Exception as e:
        logger.error(f"Error getting articles: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "articles": []
        })

@app.route('/api/articles/<article_id>', methods=['GET'])
def get_article(article_id):
    """
    Get a specific article by ID.
    
    Args:
        article_id: The ID of the article to retrieve
        
    Returns:
        JSON response with the article data
    """
    try:
        # Initialize the crawler to access Redis
        crawler = get_crawler()
        
        # Get article data
        article_key = f"article:{article_id}"
        article_data = crawler.cache.get(article_key)
        
        if not article_data:
            return jsonify({
                "success": False,
                "message": f"Article not found: {article_id}"
            })
        
        return jsonify({
            "success": True,
            "article": article_data
        })
        
    except Exception as e:
        logger.error(f"Error getting article {article_id}: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route('/api/articles/<article_id>/summarize', methods=['POST'])
def summarize_article(article_id):
    """
    Generate a summary for a specific article.
    
    Args:
        article_id: The ID of the article to summarize
        
    Returns:
        JSON response with the generated summary
    """
    try:
        # Initialize the crawler to access Redis
        crawler = get_crawler()
        
        # Get article data
        article_key = f"article:{article_id}"
        article_data = crawler.cache.get(article_key)
        
        if not article_data:
            return jsonify({
                "success": False,
                "message": f"Article not found: {article_id}"
            })
        
        # Generate summary using OpenAI
        summary = crawler._generate_summary_with_llm(article_data)
        
        if not summary:
            return jsonify({
                "success": False,
                "message": "Failed to generate summary"
            })
        
        # Update article data with new summary
        article_data['summary'] = summary
        article_data['summary_generated_at'] = datetime.now().isoformat()
        crawler.cache.set(article_key, article_data)
        
        return jsonify({
            "success": True,
            "summary": summary,
            "article_id": article_id
        })
        
    except Exception as e:
        logger.error(f"Error summarizing article {article_id}: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route('/api/articles/summarize-batch', methods=['POST'])
def summarize_batch():
    """
    Generate summaries for multiple articles in a batch.
    
    Expected JSON body:
    - client_id: Filter articles by client ID (optional)
    - limit: Maximum number of articles to summarize (default: 10)
    
    Returns:
        JSON response with results
    """
    try:
        # Get request body
        body = request.get_json() or {}
        client_id = body.get('client_id')
        limit = int(body.get('limit', 10))
        
        # Import the auto-summarization function
        from src.utils.auto_summarize import auto_summarize_articles
        
        # Run the auto-summarization
        count = auto_summarize_articles(limit)
        
        return jsonify({
            "success": True,
            "count": count,
            "message": f"Successfully summarized {count} articles"
        })
        
    except Exception as e:
        logger.error(f"Error summarizing articles in batch: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e)
        })

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """
    Get a list of all clients.
    
    Returns:
        JSON response with clients
    """
    try:
        # Get client model
        client_model = get_client_model()
        
        # Get all clients
        clients = client_model.get_all_clients()
        
        return jsonify({
            "success": True,
            "count": len(clients),
            "clients": clients
        })
        
    except Exception as e:
        logger.error(f"Error getting clients: {str(e)}")
        return jsonify({
            "success": False,
            "message": str(e),
            "clients": []
        })

# Static files route for templates and assets
@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files from the templates directory."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return send_from_directory(templates_dir, filename)

# Dashboard routes
@app.route('/')
@app.route('/dashboard')
def dashboard():
    """Serve the dashboard page."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return send_from_directory(templates_dir, 'dashboard.html')

@app.route('/clients')
def clients_page():
    """Serve the clients page."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return send_from_directory(templates_dir, 'clients.html')

@app.route('/sources')
def sources_page():
    """Serve the sources page."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return send_from_directory(templates_dir, 'sources.html')

@app.route('/reports')
def reports_page():
    """Serve the reports page."""
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    return send_from_directory(templates_dir, 'reports.html')

def run_api_server(host='0.0.0.0', port=5000, debug=False):
    """Run the Flask API server."""
    app.run(host=host, port=port, debug=debug)

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the API server
    run_api_server(debug=True) 