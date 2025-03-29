#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Market Intelligence Platform Main Application

This is the main entry point for the Market Intelligence Platform.
It provides a command-line interface to run different components of the system.
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv

from src.init import initialize_system, setup_demo_system, add_default_sources, add_demo_clients, crawl_initial_data
from src.collectors.simple_crawler import get_crawler
from src.crawl_scheduler import get_scheduler
from src.generators.report_generator import get_report_generator
from src.generators.linkedin_generator import get_linkedin_generator
from src.models.client_model import get_client_model
from src.utils.file_utils import ensure_dir_exists, save_file_content
from src.utils.auto_summarize import auto_summarize_articles

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Market Intelligence Platform')
    
    # Setup subparsers for different commands
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Set up the system')
    setup_parser.add_argument('--demo', action='store_true', help='Set up with demo data')
    setup_parser.add_argument('--force', action='store_true', help='Force setup even if data exists')
    
    # Crawl command
    crawl_parser = subparsers.add_parser('crawl', help='Crawl sources')
    crawl_parser.add_argument('--url', help='Specific URL to crawl')
    crawl_parser.add_argument('--all', action='store_true', help='Crawl all sources')
    crawl_parser.add_argument('--source-id', help='Specific source ID to crawl')
    
    # Report command
    report_parser = subparsers.add_parser('report', help='Generate reports')
    report_parser.add_argument('--client-id', required=True, help='Client ID to generate report for')
    report_parser.add_argument('--type', choices=['daily', 'weekly', 'monthly'], default='daily', help='Report type')
    report_parser.add_argument('--output', choices=['markdown', 'html', 'pdf', 'all'], default='all', help='Output format')
    
    # LinkedIn command
    linkedin_parser = subparsers.add_parser('linkedin', help='Generate LinkedIn content')
    linkedin_parser.add_argument('--client-id', help='Client ID to base content on')
    linkedin_parser.add_argument('--article-id', help='Specific article ID to use')
    linkedin_parser.add_argument('--topic', help='Topic to focus on')
    linkedin_parser.add_argument('--batch', type=int, help='Generate a batch of posts')
    
    # Client command
    client_parser = subparsers.add_parser('client', help='Manage clients')
    client_parser.add_argument('--list', action='store_true', help='List all clients')
    client_parser.add_argument('--create', action='store_true', help='Create a new client')
    client_parser.add_argument('--name', help='Client name')
    client_parser.add_argument('--interests', help='Comma-separated interests')
    
    # Source command
    source_parser = subparsers.add_parser('source', help='Manage sources')
    source_parser.add_argument('--list', action='store_true', help='List all sources')
    source_parser.add_argument('--add', action='store_true', help='Add a new source')
    source_parser.add_argument('--url', help='Source URL')
    source_parser.add_argument('--name', help='Source name')
    source_parser.add_argument('--category', help='Source category')
    source_parser.add_argument('--tags', help='Comma-separated tags')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the scheduler')
    run_parser.add_argument('--daemon', action='store_true', help='Run as a daemon')
    
    # Summarize command
    summarize_parser = subparsers.add_parser('summarize', help='Auto-summarize articles')
    summarize_parser.add_argument('--limit', type=int, default=10, help='Maximum number of articles to summarize')
    summarize_parser.add_argument('--force', action='store_true', help='Force summarization even for articles with existing summaries')
    
    # Web server command
    web_parser = subparsers.add_parser('web', help='Start the web server')
    web_parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    web_parser.add_argument('--port', type=int, default=5000, help='Port to listen on')
    web_parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    
    return parser.parse_args()

def handle_setup(args):
    """Handle setup command."""
    if args.demo:
        logger.info("Setting up demo system...")
        result = setup_demo_system()
        logger.info(f"Demo setup complete. Status: {json.dumps(result['status'])}")
    else:
        logger.info("Initializing system...")
        result = initialize_system()
        logger.info("System initialized.")
        
        if args.force:
            add_default_sources(force=True)
            add_demo_clients(force=True)

def handle_crawl(args):
    """Handle crawl command."""
    crawler = get_crawler()
    scheduler = get_scheduler()
    
    if args.url:
        logger.info(f"Crawling URL: {args.url}")
        result = crawler.crawl_url(args.url)
        logger.info(f"Crawl {'successful' if result['success'] else 'failed'}")
        logger.info(f"Title: {result['title']}")
        logger.info(f"ID: {result['id']}")
    elif args.source_id:
        logger.info(f"Crawling source ID: {args.source_id}")
        result = scheduler.crawl_source(args.source_id)
        if result:
            logger.info(f"Crawl {'successful' if result['success'] else 'failed'}")
            logger.info(f"Title: {result['title']}")
        else:
            logger.error(f"Source not found: {args.source_id}")
    elif args.all:
        logger.info("Crawling all sources...")
        results = scheduler.crawl_all_sources()
        success_count = sum(1 for r in results if r.get('success', False))
        logger.info(f"Crawled {len(results)} sources, {success_count} successful")
    else:
        logger.error("No crawl action specified. Use --url, --source-id, or --all")

def handle_report(args):
    """Handle report command."""
    client_id = args.client_id
    report_type = args.type
    
    output_formats = ['markdown', 'html', 'pdf'] if args.output == 'all' else [args.output]
    
    report_generator = get_report_generator()
    client_model = get_client_model()
    
    # Check if client exists
    client = client_model.get_client(client_id)
    if not client:
        logger.error(f"Client not found: {client_id}")
        return
    
    logger.info(f"Generating {report_type} report for client: {client['name']}")
    report = report_generator.generate_report(
        client_id=client_id,
        report_type=report_type,
        output_formats=output_formats
    )
    
    if report.get('success', False):
        logger.info(f"Report generated successfully (ID: {report['id']})")
        
        # Log available formats
        formats = list(report['content'].keys())
        logger.info(f"Available formats: {', '.join(formats)}")
        
        # Print path to the report file
        if 'markdown' in report['content']:
            md_path = os.path.join(report_generator.reports_dir, report['id'], f"{report_type}_report.md")
            logger.info(f"Report saved at: {md_path}")
    else:
        error = report.get('error', 'Unknown error')
        logger.error(f"Failed to generate report: {error}")

def handle_linkedin(args):
    """Handle LinkedIn command."""
    linkedin_generator = get_linkedin_generator()
    
    if args.batch:
        count = args.batch
        logger.info(f"Generating batch of {count} LinkedIn posts")
        
        topics = [t.strip() for t in args.topic.split(',')] if args.topic else None
        
        posts = linkedin_generator.generate_posts_batch(
            count=count,
            topics=topics,
            client_id=args.client_id
        )
        
        success_count = len(posts)
        logger.info(f"Generated {success_count} LinkedIn posts")
        
        for i, post in enumerate(posts, 1):
            logger.info(f"Post {i} - ID: {post['id']}, Article: {post['article_title']}")
    else:
        logger.info("Generating LinkedIn post")
        
        post = linkedin_generator.generate_post(
            article_id=args.article_id,
            topic=args.topic,
            client_id=args.client_id
        )
        
        if post.get('success', False):
            logger.info(f"Post generated successfully (ID: {post['id']})")
            logger.info(f"Based on article: {post['article_title']}")
            post_path = os.path.join(linkedin_generator.content_dir, post['id'], "post.txt")
            logger.info(f"Post saved at: {post_path}")
        else:
            error = post.get('error', 'Unknown error')
            logger.error(f"Failed to generate post: {error}")

def handle_client(args):
    """Handle client command."""
    client_model = get_client_model()
    
    if args.list:
        clients = client_model.get_all_clients()
        logger.info(f"Found {len(clients)} clients:")
        
        for client in clients:
            logger.info(f"ID: {client['id']}")
            logger.info(f"Name: {client['name']}")
            logger.info(f"Interests: {', '.join(client['interests'])}")
            logger.info("---")
    elif args.create:
        if not args.name or not args.interests:
            logger.error("Name and interests are required to create a client")
            return
        
        interests = [i.strip() for i in args.interests.split(',')]
        
        logger.info(f"Creating client: {args.name}")
        client = client_model.create_client(
            name=args.name,
            interests=interests
        )
        
        logger.info(f"Client created successfully (ID: {client['id']})")
    else:
        logger.error("No client action specified. Use --list or --create")

def handle_source(args):
    """Handle source command."""
    scheduler = get_scheduler()
    
    if args.list:
        sources = scheduler.get_sources()
        logger.info(f"Found {len(sources)} sources:")
        
        for source in sources:
            logger.info(f"ID: {source['id']}")
            logger.info(f"Name: {source['name']}")
            logger.info(f"URL: {source['url']}")
            logger.info(f"Category: {source['category']}")
            logger.info(f"Tags: {', '.join(source['client_tags'])}")
            logger.info(f"Last crawled: {source['last_crawled'] or 'Never'}")
            logger.info("---")
    elif args.add:
        if not args.url or not args.name or not args.category:
            logger.error("URL, name, and category are required to add a source")
            return
        
        tags = [t.strip() for t in args.tags.split(',')] if args.tags else []
        
        logger.info(f"Adding source: {args.name}")
        source = scheduler.add_source(
            url=args.url,
            name=args.name,
            category=args.category,
            client_tags=tags
        )
        
        logger.info(f"Source added successfully (ID: {source['id']})")
    else:
        logger.error("No source action specified. Use --list or --add")

def handle_run(args):
    """Handle run command."""
    scheduler = get_scheduler()
    
    # Initialize system
    initialize_system()
    
    # Schedule all sources
    scheduler.schedule_all_sources()
    
    logger.info("Scheduler started. Press Ctrl+C to exit.")
    
    try:
        # Keep the script running
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")

def handle_summarize(args):
    """Handle summarize command."""
    limit = args.limit
    force = args.force
    
    logger.info(f"Auto-summarizing up to {limit} articles (force={force})...")
    
    # If force is True, we should implement logic to clear existing summaries
    if force:
        crawler = get_crawler()
        article_ids = crawler.cache.get_keys("article:*")
        logger.info(f"Clearing existing summaries from {len(article_ids)} articles...")
        
        for article_id in article_ids:
            article_data = crawler.cache.get(article_id)
            if article_data and isinstance(article_data, dict) and 'summary' in article_data:
                # Clear the summary and summary_generated_at fields
                article_data.pop('summary', None)
                article_data.pop('summary_generated_at', None)
                crawler.cache.set(article_id, article_data)
    
    # Perform the auto-summarization
    count = auto_summarize_articles(limit)
    
    logger.info(f"Successfully summarized {count} articles")
    
    return {
        "success": True,
        "articles_summarized": count
    }

def handle_web(args):
    """Handle web server command."""
    from src.api_routes import app, run_api_server
    
    host = args.host
    port = args.port
    debug = args.debug
    
    logger.info(f"Starting web server on {host}:{port} (debug={debug})")
    run_api_server(host=host, port=port, debug=debug)

def main():
    """Main entry point."""
    args = parse_arguments()
    
    if args.command == 'setup':
        handle_setup(args)
    elif args.command == 'crawl':
        handle_crawl(args)
    elif args.command == 'report':
        handle_report(args)
    elif args.command == 'linkedin':
        handle_linkedin(args)
    elif args.command == 'client':
        handle_client(args)
    elif args.command == 'source':
        handle_source(args)
    elif args.command == 'run':
        handle_run(args)
    elif args.command == 'summarize':
        handle_summarize(args)
    elif args.command == 'web':
        handle_web(args)
    else:
        logger.error("No command specified. Try 'setup', 'crawl', 'report', 'linkedin', 'client', 'source', 'run', 'summarize', or 'web'.")

if __name__ == "__main__":
    main() 