#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import glob
import logging
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, render_template

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__, 
    static_folder='../reports',
    template_folder='templates'
)

# Ensure reports directory exists
reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
os.makedirs(reports_dir, exist_ok=True)

@app.route('/')
def index():
    """Serve the landing page"""
    return render_template('index.html')

@app.route('/api/reports')
def list_reports():
    """List the available reports, optionally filtered by client and frequency"""
    try:
        # Get query parameters
        client = request.args.get('client', 'general')
        frequency = request.args.get('frequency', 'daily')
        
        # Create the path for the specified client and frequency
        client_dir = client.lower().replace(" ", "_")
        reports_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
        client_reports_dir = os.path.join(reports_base_dir, client_dir, frequency)
        
        # If the directory doesn't exist, fall back to the default directory
        if not os.path.exists(client_reports_dir):
            client_reports_dir = reports_base_dir
        
        reports = []
        
        # Get all consolidated report markdown files
        md_files = glob.glob(os.path.join(client_reports_dir, 'consolidated_report_*.md'))
        
        # Sort by timestamp (newest first)
        md_files.sort(key=os.path.getmtime, reverse=True)
        
        # Limit to 10 most recent reports
        md_files = md_files[:10]
        
        for md_file in md_files:
            base_name = os.path.basename(md_file)
            timestamp = base_name.replace('consolidated_report_', '').replace('.md', '')
            
            # Parse timestamp
            try:
                date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                formatted_date = date_obj.strftime('%B %d, %Y')
                formatted_time = date_obj.strftime('%I:%M %p')  # Format time as 12-hour with AM/PM
            except:
                formatted_date = "Unknown Date"
                formatted_time = "Unknown Time"
            
            # Get corresponding HTML and PDF files
            html_file = md_file.replace('.md', '.html')
            pdf_file = md_file.replace('.md', '.pdf')
            
            # Get first 200 characters of report as description
            description = ""
            client_name = client.capitalize()
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    description = content[:200] + "..."
            except:
                description = f"{frequency.capitalize()} business intelligence report."
            
            # Calculate relative path for URLs based on client directory
            relative_dir = os.path.relpath(os.path.dirname(md_file), reports_base_dir)
            
            report_info = {
                "title": f"Business Intelligence Report - {formatted_date}",
                "client": client_name,
                "frequency": frequency,
                "date": date_obj.isoformat() if 'date_obj' in locals() else "",
                "formatted_date": formatted_date,
                "formatted_time": formatted_time,
                "timestamp": timestamp,
                "description": description,
                "md_url": f"/reports/{relative_dir}/{os.path.basename(md_file)}",
                "html_url": f"/reports/{relative_dir}/{os.path.basename(html_file)}",
                "pdf_url": f"/reports/{relative_dir}/{os.path.basename(pdf_file)}"
            }
            
            reports.append(report_info)
        
        return jsonify({"reports": reports})
    
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        return jsonify({"error": str(e), "reports": []}), 500

@app.route('/reports/<path:path>')
def serve_report(path):
    """Serve a report file"""
    return send_from_directory('../reports', path)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True) 