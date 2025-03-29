#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Dashboard Module for Market Intelligence Platform.

This module provides a web dashboard for viewing client reports,
managing clients, and generating LinkedIn content.
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from flask import Flask, render_template, request, jsonify, redirect, url_for, Response, send_file, flash
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

from src.crawler import get_crawler
from src.report_generator import get_report_generator
from src.linkedin_generator import get_linkedin_generator
from src.models.client_model import get_client_model
from src.utils.redis_cache import get_redis_cache
from src.document_processor import process_document  # Assuming you'll implement this

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize the dashboard app
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'))
CORS(app)

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'csv', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'development-key')

# Initialize services
crawler = get_crawler()
report_generator = get_report_generator()
linkedin_generator = get_linkedin_generator()
client_model = get_client_model()
redis_cache = get_redis_cache()

def allowed_file(filename):
    """Check if file type is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Render the dashboard home page."""
    clients = client_model.get_all_clients()
    return render_template('index.html', clients=clients)

@app.route('/clients')
def list_clients():
    """List all clients."""
    clients = client_model.get_all_clients()
    
    # Enhance client data with counts and dates
    for client in clients:
        client_id = client.get('id')
        # Get report count
        report_history_key = f"client:{client_id}:report_history"
        report_history = redis_cache.get(report_history_key) or []
        client['reports_count'] = len(report_history)
        
        # Get latest report date
        if report_history:
            latest_report_id = report_history[0]
            report_data = redis_cache.get(f"report:{latest_report_id}")
            if report_data and 'generated_at' in report_data:
                client['latest_report_date'] = datetime.fromisoformat(report_data['generated_at']).strftime("%Y-%m-%d %H:%M")
        
        # Get article count
        article_key = f"client:{client_id}:articles"
        articles = redis_cache.get(article_key) or []
        client['articles_count'] = len(articles)
    
    return render_template('clients.html', clients=clients)

@app.route('/clients/add', methods=['GET', 'POST'])
def add_client():
    """Add a new client."""
    if request.method == 'POST':
        name = request.form.get('name')
        industry = request.form.get('industry')
        interests = request.form.get('interests', '').split(',')
        website = request.form.get('website', '')
        sources = request.form.get('sources', '').strip().split('\n')
        description = request.form.get('description', '')
        
        # Clean up interests
        interests = [i.strip() for i in interests if i.strip()]
        # Clean up sources
        sources = [s.strip() for s in sources if s.strip()]
        
        if name:
            client = client_model.create_client(
                name=name,
                industry=industry,
                interests=interests,
                website=website,
                sources=sources,
                description=description
            )
            
            # Trigger initial crawl for the new client if sources are provided
            client_id = client.get('id')
            if sources:
                try:
                    crawler.crawl_sources_for_client(client_id, sources=sources)
                    flash(f"Started crawling {len(sources)} sources for {name}", "success")
                except Exception as e:
                    logger.error(f"Error crawling for new client {client_id}: {str(e)}")
                    flash(f"Error starting crawl: {str(e)}", "error")
            
            return redirect(url_for('view_client', client_id=client.get('id')))
        
    return render_template('client_form.html', clients=client_model.get_all_clients())

@app.route('/clients/<client_id>')
def view_client(client_id):
    """View a specific client's dashboard."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    # Format client data for template
    if isinstance(client.get('interests'), list):
        client['interests_list'] = client['interests']
        client['interests'] = ', '.join(client['interests'])
    
    # Get the latest report
    latest_report = report_generator.get_client_report(client_id)
    
    # Get recent articles
    recent_articles = crawler.get_client_articles(client_id, limit=10)
    
    return render_template('client_detail.html', 
                          client=client, 
                          latest_report=latest_report,
                          recent_articles=recent_articles)

@app.route('/clients/<client_id>/edit', methods=['GET', 'POST'])
def edit_client(client_id):
    """Edit a client."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    # Format client data for template
    if isinstance(client.get('interests'), list):
        client['interests_list'] = client['interests']
        client['interests'] = ', '.join(client['interests'])
    
    if request.method == 'POST':
        name = request.form.get('name')
        industry = request.form.get('industry')
        interests = request.form.get('interests', '').split(',')
        website = request.form.get('website', '')
        sources = request.form.get('sources', '').strip().split('\n')
        description = request.form.get('description', '')
        
        # Clean up interests and sources
        interests = [i.strip() for i in interests if i.strip()]
        sources = [s.strip() for s in sources if s.strip()]
        
        if name:
            updated_client = client_model.update_client(
                client_id=client_id,
                name=name,
                industry=industry,
                interests=interests,
                website=website,
                sources=sources,
                description=description
            )
            
            flash(f"Client {name} updated successfully", "success")
            return redirect(url_for('view_client', client_id=client_id))
    
    return render_template('client_form.html', client=client, clients=client_model.get_all_clients())

@app.route('/clients/<client_id>/delete', methods=['POST'])
def delete_client(client_id):
    """Delete a client and all associated data."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    # Delete all client data from Redis
    try:
        client_name = client.get('name', 'Unknown')
        client_model.delete_client(client_id)
        flash(f"Client {client_name} and all associated data deleted", "success")
    except Exception as e:
        logger.error(f"Error deleting client {client_id}: {str(e)}")
        flash(f"Error deleting client: {str(e)}", "error")
    
    return redirect(url_for('list_clients'))

@app.route('/clients/<client_id>/crawl', methods=['POST'])
def crawl_for_client(client_id):
    """Trigger a crawl for a specific client."""
    client = client_model.get_client(client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found"})
    
    try:
        # Get sources from client or use defaults
        sources = client.get('sources', [])
        
        results = crawler.crawl_sources_for_client(client_id, sources=sources, force_update=True)
        return jsonify({
            "success": True, 
            "message": f"Crawled {len(results)} articles for {client.get('name')}",
            "articles_count": len(results)
        })
    except Exception as e:
        logger.error(f"Error crawling for client {client_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/clients/<client_id>/generate-report', methods=['POST'])
def generate_client_report(client_id):
    """Generate a new report for a specific client."""
    client = client_model.get_client(client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found"})
    
    try:
        # Option to force crawl before generating
        force_crawl = request.form.get('force_crawl') == 'true'
        
        report_data = report_generator.generate_client_report(client_id, force_crawl=force_crawl)
        if report_data:
            return jsonify({
                "success": True,
                "message": f"Generated report for {client.get('name')}",
                "report_id": report_data.get('id')
            })
        else:
            return jsonify({"success": False, "error": "Failed to generate report"})
    except Exception as e:
        logger.error(f"Error generating report for client {client_id}: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/clients/<client_id>/reports')
def client_reports(client_id):
    """View a client's report history."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    reports = report_generator.get_client_report_history(client_id)
    
    # Format reports for the template
    for report in reports:
        # Extract summary from content
        content = report.get('content', '')
        summary = content[:500] + '...' if len(content) > 500 else content
        report['summary'] = summary
        
        # Add topics count based on client interests
        report['topics_count'] = len(client.get('interests', [])) 
        
        # Format date
        if 'generated_at' in report:
            report['date'] = datetime.fromisoformat(report['generated_at']).strftime("%Y-%m-%d %H:%M")
    
    return render_template('reports_list.html', client=client, reports=reports)

@app.route('/clients/<client_id>/reports/<report_id>')
def view_report(client_id, report_id):
    """View a specific report."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    report_data = report_generator.get_client_report(client_id, report_id)
    if not report_data:
        flash("Report not found", "error")
        return redirect(url_for('client_reports', client_id=client_id))
    
    # Format date
    if 'generated_at' in report_data:
        report_data['date'] = datetime.fromisoformat(report_data['generated_at']).strftime("%Y-%m-%d %H:%M")
    
    # Get referenced articles if available
    if 'articles_ids' in report_data and report_data['articles_ids']:
        articles = []
        for article_id in report_data['articles_ids']:
            article = redis_cache.get(f"article:{article_id}")
            if article:
                articles.append(article)
        report_data['articles'] = articles
    
    return render_template('report.html', client=client, report=report_data)

@app.route('/clients/<client_id>/reports/<report_id>/export')
def export_report(client_id, report_id):
    """Export a report as PDF."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    report_data = report_generator.get_client_report(client_id, report_id)
    if not report_data:
        flash("Report not found", "error")
        return redirect(url_for('client_reports', client_id=client_id))
    
    try:
        # Generate PDF from report content
        from weasyprint import HTML, CSS
        from io import BytesIO
        
        # Format report data
        if 'generated_at' in report_data:
            report_data['date'] = datetime.fromisoformat(report_data['generated_at']).strftime("%Y-%m-%d %H:%M")
        
        # Generate HTML for the report
        client_name = client.get('name', 'Client')
        report_date = report_data.get('date', datetime.now().strftime("%Y-%m-%d"))
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{client_name} - Market Intelligence Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                h1 {{ color: #333; border-bottom: 1px solid #ddd; padding-bottom: 10px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .footer {{ text-align: center; margin-top: 30px; font-size: 0.9em; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>{client_name} - Market Intelligence Report</h1>
                <p>Generated on: {report_date}</p>
            </div>
            
            <div class="content">
                {report_data.get('content', 'No content available.')}
            </div>
            
            <div class="footer">
                <p>Generated by Market Intelligence Platform</p>
                <p>Confidential - For internal use only</p>
            </div>
        </body>
        </html>
        """
        
        # Generate PDF
        pdf_file = BytesIO()
        HTML(string=html_content).write_pdf(pdf_file)
        pdf_file.seek(0)
        
        filename = f"{client_name}_Report_{report_date.replace(' ', '_').replace(':', '')}.pdf"
        return send_file(
            pdf_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Error exporting report: {str(e)}")
        flash(f"Error exporting report: {str(e)}", "error")
        return redirect(url_for('view_report', client_id=client_id, report_id=report_id))

@app.route('/clients/<client_id>/upload', methods=['GET', 'POST'])
def upload_file(client_id):
    """Upload and process external files for a client."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    if request.method == 'POST':
        # Check if file part exists
        if 'file' not in request.files:
            flash('No file part', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        
        # Check if a file was selected
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            # Secure the filename and save the file
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            # Process the file
            try:
                # Extract text from the file
                extracted_text, metadata = process_document(file_path)
                
                # Store in Redis
                external_data = {
                    'id': f"external-{int(time.time())}",
                    'filename': filename,
                    'upload_date': datetime.now().isoformat(),
                    'content': extracted_text,
                    'metadata': metadata
                }
                
                # Save to Redis
                external_data_key = f"client:{client_id}:external_data:{external_data['id']}"
                redis_cache.set(external_data_key, external_data)
                
                # Update list of external data
                external_data_list_key = f"client:{client_id}:external_data_list"
                external_data_list = redis_cache.get(external_data_list_key) or []
                external_data_list.append(external_data['id'])
                redis_cache.set(external_data_list_key, external_data_list)
                
                flash(f"File {filename} processed and stored successfully", "success")
                
                # Optionally generate a report from this data
                generate_report = request.form.get('generate_report') == 'true'
                if generate_report:
                    # Call report generator with the external data
                    # This would need to be implemented in the report generator
                    pass
                
                return redirect(url_for('view_client', client_id=client_id))
                
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}")
                flash(f"Error processing file: {str(e)}", "error")
                return redirect(request.url)
    
    # GET request - show upload form
    return render_template('upload_file.html', client=client)

@app.route('/linkedin')
def linkedin_posts():
    """View all LinkedIn posts."""
    # Get all LinkedIn posts from Redis
    posts_key = "linkedin:posts"
    post_ids = redis_cache.get(posts_key) or []
    
    posts = []
    for post_id in post_ids:
        post_data = linkedin_generator.get_post(post_id)
        if post_data:
            # Format date
            if 'created_at' in post_data:
                post_data['date'] = datetime.fromisoformat(post_data['created_at']).strftime("%Y-%m-%d %H:%M")
            
            # Add client name if client_id exists
            if 'client_id' in post_data:
                client = client_model.get_client(post_data['client_id'])
                if client:
                    post_data['client_name'] = client.get('name', 'Unknown Client')
            
            posts.append(post_data)
    
    # Sort posts by date, newest first
    posts.sort(key=lambda x: x.get('date', ''), reverse=True)
    
    return render_template('linkedin.html', posts=posts, clients=client_model.get_all_clients())

@app.route('/linkedin/new', methods=['GET', 'POST'])
def create_linkedin_post():
    """Create a new LinkedIn post manually."""
    if request.method == 'POST':
        client_id = request.form.get('client_id')
        content = request.form.get('content')
        hashtags = request.form.get('hashtags')
        tone = request.form.get('tone', 'professional')
        
        if not client_id or not content:
            flash("Client and content are required", "error")
            return redirect(request.url)
        
        try:
            # Handle image upload if present
            image_url = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '':
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(file_path)
                    # Store image and get URL - this would need to be implemented
                    image_url = f"/uploads/{filename}"
            
            # Generate image with AI if requested
            generated_image = request.form.get('generate_image') == '1'
            
            # Create the post manually
            post_data = {
                'id': f"post-{int(time.time())}",
                'client_id': client_id,
                'content': content,
                'hashtags': hashtags,
                'tone': tone,
                'source_type': 'manual',
                'created_at': datetime.now().isoformat(),
                'image_url': image_url,
                'generated_image': generated_image
            }
            
            # Store the post
            linkedin_generator._store_linkedin_post(post_data)
            
            flash("LinkedIn post created successfully", "success")
            return redirect(url_for('linkedin_posts'))
            
        except Exception as e:
            logger.error(f"Error creating LinkedIn post: {str(e)}")
            flash(f"Error creating post: {str(e)}", "error")
            return redirect(request.url)
    
    # GET request - show form
    return render_template('linkedin_form.html', clients=client_model.get_all_clients())

@app.route('/clients/<client_id>/reports/<report_id>/linkedin', methods=['GET', 'POST'])
def create_linkedin_from_report(client_id, report_id):
    """Create a LinkedIn post from a report."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    report_data = report_generator.get_client_report(client_id, report_id)
    if not report_data:
        flash("Report not found", "error")
        return redirect(url_for('client_reports', client_id=client_id))
    
    if request.method == 'POST':
        tone = request.form.get('tone', 'professional')
        
        try:
            post_data = linkedin_generator.generate_post_from_report(client_id, report_id, tone)
            
            if post_data:
                flash("LinkedIn post created successfully", "success")
                return redirect(url_for('linkedin_posts'))
            else:
                flash("Failed to generate LinkedIn post", "error")
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating LinkedIn post: {str(e)}")
            flash(f"Error creating post: {str(e)}", "error")
            return redirect(request.url)
    
    # Format report date
    if 'generated_at' in report_data:
        report_data['date'] = datetime.fromisoformat(report_data['generated_at']).strftime("%Y-%m-%d %H:%M")
    
    # GET request - show form
    return render_template('linkedin_form.html', 
                          client=client, 
                          source_type='report',
                          source_id=report_id,
                          source_title=f"Report from {report_data.get('date', 'unknown date')}")

@app.route('/clients/<client_id>/articles/<article_id>/linkedin', methods=['GET', 'POST'])
def create_linkedin_from_article(client_id, article_id):
    """Create a LinkedIn post from an article."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    # Get article data
    article = redis_cache.get(f"article:{article_id}")
    if not article:
        flash("Article not found", "error")
        return redirect(url_for('view_client', client_id=client_id))
    
    if request.method == 'POST':
        tone = request.form.get('tone', 'professional')
        
        try:
            post_data = linkedin_generator.generate_post_from_article(article_id, tone)
            
            if post_data:
                flash("LinkedIn post created successfully", "success")
                return redirect(url_for('linkedin_posts'))
            else:
                flash("Failed to generate LinkedIn post", "error")
                return redirect(request.url)
                
        except Exception as e:
            logger.error(f"Error creating LinkedIn post: {str(e)}")
            flash(f"Error creating post: {str(e)}", "error")
            return redirect(request.url)
    
    # GET request - show form
    return render_template('linkedin_form.html', 
                          client=client, 
                          source_type='article',
                          source_id=article_id,
                          source_title=article.get('title', 'Untitled Article'))

@app.route('/api/crawl-all', methods=['POST'])
def api_crawl_all():
    """API endpoint to crawl for all clients."""
    try:
        clients = client_model.get_all_clients()
        results = []
        
        for client in clients:
            client_id = client.get('id')
            try:
                sources = client.get('sources', [])
                articles = crawler.crawl_sources_for_client(client_id, sources=sources)
                results.append({
                    "client_id": client_id,
                    "client_name": client.get('name'),
                    "articles_count": len(articles),
                    "success": True
                })
            except Exception as e:
                results.append({
                    "client_id": client_id,
                    "client_name": client.get('name'),
                    "error": str(e),
                    "success": False
                })
        
        return jsonify({
            "success": True,
            "results": results,
            "clients_count": len(clients)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/generate-all-reports', methods=['POST'])
def api_generate_all_reports():
    """API endpoint to generate reports for all clients."""
    try:
        reports = report_generator.generate_reports_for_all_clients()
        return jsonify({
            "success": True,
            "message": f"Generated {len(reports)} reports",
            "reports_count": len(reports)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/generate-linkedin-content', methods=['POST'])
def api_generate_linkedin_content():
    """API endpoint to generate LinkedIn content using AI."""
    data = request.json
    client_id = data.get('client_id')
    tone = data.get('tone', 'professional')
    
    if not client_id:
        return jsonify({"success": False, "error": "Client ID is required"})
    
    client = client_model.get_client(client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found"})
    
    try:
        # Get latest report
        report_data = report_generator.get_client_report(client_id)
        if not report_data:
            return jsonify({"success": False, "error": "No reports found for this client"})
        
        # Generate content using the LinkedIn generator
        post_content, hashtags = linkedin_generator._generate_post_content({
            'client': client,
            'content': report_data.get('content', ''),
            'type': 'report'
        }, tone)
        
        if not post_content:
            return jsonify({"success": False, "error": "Failed to generate content"})
        
        return jsonify({
            "success": True,
            "content": post_content,
            "hashtags": ' '.join(hashtags) if hashtags else ""
        })
    except Exception as e:
        logger.error(f"Error generating LinkedIn content: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/clients/<client_id>/external_data')
def list_external_data(client_id):
    """View all external data files for a client."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))

    # Get list of external data files
    external_data_list_key = f"client:{client_id}:external_data_list"
    external_data_ids = redis_cache.get(external_data_list_key) or []
    
    external_data = []
    for data_id in external_data_ids:
        data_key = f"client:{client_id}:external_data:{data_id}"
        data = redis_cache.get(data_key)
        if data:
            # Format date for display
            if 'upload_date' in data:
                try:
                    data['upload_date'] = datetime.fromisoformat(data['upload_date']).strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    pass
            
            external_data.append(data)
    
    # Sort by upload date, newest first
    external_data.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
    
    return render_template('external_data.html', client=client, external_data=external_data)

@app.route('/clients/<client_id>/external_data/<data_id>/view')
def view_external_data(client_id, data_id):
    """View a specific external data file."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    data_key = f"client:{client_id}:external_data:{data_id}"
    file_data = redis_cache.get(data_key)
    
    if not file_data:
        flash("File not found", "error")
        return redirect(url_for('list_external_data', client_id=client_id))
    
    # Format date for display
    if 'upload_date' in file_data:
        try:
            file_data['upload_date'] = datetime.fromisoformat(file_data['upload_date']).strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            pass
    
    # Get content
    content = file_data.get('content', '')
    
    # For tabular data, split into lines for the table view
    content_lines = None
    if file_data.get('filename', '').endswith(('.csv', '.xlsx', '.xls')):
        content_lines = content.split('\n')
    
    return render_template('view_external_data.html', 
                          client=client, 
                          file=file_data, 
                          content=content,
                          content_lines=content_lines)

@app.route('/clients/<client_id>/external_data/<data_id>/generate_report', methods=['GET', 'POST'])
def generate_report_from_file(client_id, data_id):
    """Generate a report from an external data file."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    data_key = f"client:{client_id}:external_data:{data_id}"
    file_data = redis_cache.get(data_key)
    
    if not file_data:
        flash("File not found", "error")
        return redirect(url_for('list_external_data', client_id=client_id))
    
    try:
        # Call the report generator with the file content
        # This would need to be implemented in the report generator
        report_data = report_generator.generate_report_from_external_data(
            client_id,
            file_data.get('content', ''),
            file_data.get('filename', ''),
            file_data.get('metadata', {})
        )
        
        if report_data:
            flash(f"Generated report from {file_data.get('filename')}", "success")
            return redirect(url_for('view_report', client_id=client_id, report_id=report_data.get('id')))
        else:
            flash("Failed to generate report", "error")
            return redirect(url_for('view_external_data', client_id=client_id, data_id=data_id))
    except Exception as e:
        logger.error(f"Error generating report from file: {str(e)}")
        flash(f"Error generating report: {str(e)}", "error")
        return redirect(url_for('view_external_data', client_id=client_id, data_id=data_id))

@app.route('/clients/<client_id>/external_data/<data_id>/delete', methods=['POST'])
def delete_external_data(client_id, data_id):
    """Delete an external data file."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    data_key = f"client:{client_id}:external_data:{data_id}"
    file_data = redis_cache.get(data_key)
    
    if not file_data:
        flash("File not found", "error")
        return redirect(url_for('list_external_data', client_id=client_id))
    
    try:
        # Delete the file data from Redis
        redis_cache.delete(data_key)
        
        # Update the external data list
        external_data_list_key = f"client:{client_id}:external_data_list"
        external_data_list = redis_cache.get(external_data_list_key) or []
        if data_id in external_data_list:
            external_data_list.remove(data_id)
            redis_cache.set(external_data_list_key, external_data_list)
        
        # Try to delete the actual file if it exists
        filename = file_data.get('filename')
        if filename:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        flash(f"Deleted file: {file_data.get('filename')}", "success")
    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        flash(f"Error deleting file: {str(e)}", "error")
    
    return redirect(url_for('list_external_data', client_id=client_id))

@app.route('/clients/<client_id>/chat')
def client_chatbot(client_id):
    """View the AI chatbot for a client."""
    client = client_model.get_client(client_id)
    if not client:
        flash("Client not found", "error")
        return redirect(url_for('list_clients'))
    
    # Get counts of available data for the client
    report_history_key = f"client:{client_id}:report_history"
    report_history = redis_cache.get(report_history_key) or []
    reports_count = len(report_history)
    
    article_key = f"client:{client_id}:articles"
    articles = redis_cache.get(article_key) or []
    articles_count = len(articles)
    
    external_data_list_key = f"client:{client_id}:external_data_list"
    external_data_list = redis_cache.get(external_data_list_key) or []
    external_data_count = len(external_data_list)
    
    # Format current time for the initial message
    current_time = datetime.now().strftime("%I:%M %p")
    
    return render_template('chatbot.html', 
                          client=client, 
                          reports_count=reports_count,
                          articles_count=articles_count,
                          external_data_count=external_data_count,
                          current_time=current_time)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """API endpoint for the chatbot."""
    data = request.json
    client_id = data.get('client_id')
    message = data.get('message')
    
    if not client_id or not message:
        return jsonify({"success": False, "error": "Client ID and message are required"})
    
    client = client_model.get_client(client_id)
    if not client:
        return jsonify({"success": False, "error": "Client not found"})
    
    try:
        # Get the latest report
        latest_report = report_generator.get_client_report(client_id)
        
        # Get recent articles
        recent_articles = crawler.get_client_articles(client_id, limit=20)
        
        # Get external data list
        external_data_list_key = f"client:{client_id}:external_data_list"
        external_data_ids = redis_cache.get(external_data_list_key) or []
        
        external_data = []
        for data_id in external_data_ids:
            data_key = f"client:{client_id}:external_data:{data_id}"
            data = redis_cache.get(data_key)
            if data:
                external_data.append(data)
        
        # Prepare context for the AI
        context = {
            "client": client,
            "latest_report": latest_report,
            "recent_articles": recent_articles,
            "external_data": external_data
        }
        
        # Process the message with OpenAI
        from src.chatbot_ai import process_chat_message
        response, sources, suggestions = process_chat_message(message, context)
        
        return jsonify({
            "success": True,
            "response": response,
            "sources": sources,
            "suggestions": suggestions
        })
        
    except Exception as e:
        logger.error(f"Error processing chat message: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

def create_app():
    """Create the Flask application."""
    # Create necessary directories
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static'), exist_ok=True)
    os.makedirs(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'), exist_ok=True)
    
    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port, debug=True)
 