#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import json
import markdown
import shutil
import tempfile
import subprocess
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import weasyprint
import re

# Setup base path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
try:
    from processors.news_analyzer import GCCBusinessNewsAnalyzer
    from generators.linkedin_content import LinkedInContentGenerator
except ImportError:
    # Fallback to direct imports for standalone testing
    pass

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('consolidated_report_generator')

class ConsolidatedReportGenerator:
    """
    Generates a consolidated report containing daily business intelligence and LinkedIn posts.
    """
    def __init__(self, reports_dir=None, standalone_mode=False, client_name="Global Possibilities Team", 
                 report_frequency="daily", include_linkedin=True, include_chatbot=True):
        """Initialize the consolidated report generator.
        
        Args:
            reports_dir: Directory to store generated reports. If None, uses default.
            standalone_mode: If True, don't initialize analyzers and generators.
            client_name: Name of the client for customized reports.
            report_frequency: Frequency of the report (daily, weekly, monthly, quarterly).
            include_linkedin: Whether to include LinkedIn posts in the report.
            include_chatbot: Whether to include the interactive chatbot in HTML reports.
        """
        # Set the reports directory
        if reports_dir:
            self.reports_dir = reports_dir
        else:
            # Use default directory within user home
            home_dir = os.path.expanduser("~")
            default_reports_dir = os.path.join(home_dir, "gp_reports")
            self.reports_dir = default_reports_dir
            
        # Create reports directory if it doesn't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Store client and report settings
        self.client_name = client_name
        self.report_frequency = report_frequency
        self.include_linkedin = include_linkedin
        self.include_chatbot = include_chatbot
        
        # Only initialize analyzers and generators if not in standalone mode
        if not standalone_mode:
            try:
                self.analyzer = GCCBusinessNewsAnalyzer(
                    config_path='config/news_sources.json',
                    model='gpt-4o'
                )
                
                self.linkedin_generator = LinkedInContentGenerator(
                    config_path='config/linkedin_config.json',
                    model='gpt-4o'
                )
            except Exception as e:
                logger.error(f"Error initializing components: {e}")
                self.analyzer = None
                self.linkedin_generator = None
        else:
            # In standalone mode, these components are not needed
            self.analyzer = None
            self.linkedin_generator = None
            
        logger.info(f"Consolidated Report Generator initialized with reports directory: {self.reports_dir}")
        logger.info(f"Client: {self.client_name}, Frequency: {self.report_frequency}")
        logger.info(f"Include LinkedIn: {self.include_linkedin}, Include Chatbot: {self.include_chatbot}")
        logger.info(f"Standalone mode: {standalone_mode}")
    
    def generate_all(self, articles=None):
        """Generate a complete report from collected articles.
        
        Args:
            articles: List of news articles collected from sources
            
        Returns:
            tuple: (markdown_path, html_path, pdf_path) - paths to the generated files
        """
        try:
            logger.info(f"Processing articles and generating report for {self.client_name}...")
            
            # If articles are provided, analyze them
            if articles and self.analyzer:
                # Process articles to generate report content
                report_text = self.analyzer.analyze_news(articles)
                
                # Generate LinkedIn posts if analyzer is available and LinkedIn is enabled
                linkedin_posts = None
                if self.linkedin_generator and self.include_linkedin:
                    linkedin_posts = self.linkedin_generator.generate_linkedin_posts(report_text)
            else:
                # For testing or when articles aren't provided
                logger.warning("No articles provided or analyzer not available")
                # Generate a simple report with placeholder content
                current_date = datetime.now().strftime("%B %d, %Y")
                report_text = f"## GCC Business Intelligence: {current_date}\n\n"
                report_text += f"Report prepared for: {self.client_name}\n\n"
                report_text += f"Report frequency: {self.report_frequency}\n\n"
                report_text += "No articles were provided for analysis. This is a placeholder report."
                linkedin_posts = None
            
            # Generate the complete report with the processed content
            return self.generate(report_text, linkedin_posts)
            
        except Exception as e:
            logger.error(f"Error in generate_all: {e}")
            return None, None, None
    
    def generate(self, report_text, linkedin_posts=None):
        """Generate a consolidated report with daily reports and LinkedIn posts."""
        try:
            # Initialize outputs
            markdown_path = None
            html_path = None
            pdf_path = None
            
            # Log the start of report generation
            logger.info("Starting consolidated report generation...")
            
            # Step 1: Create the reports directory if it doesn't exist
            os.makedirs(self.reports_dir, exist_ok=True)
            
            # Step 2: Process LinkedIn posts if provided
            if linkedin_posts and isinstance(linkedin_posts, list):
                linkedin_content = self._format_linkedin_posts(linkedin_posts)
            else:
                linkedin_content = linkedin_posts if isinstance(linkedin_posts, str) else None
                
            if not linkedin_content:
                logger.warning("No LinkedIn posts provided or failed to process LinkedIn posts")
            
            # Step 3: Create the consolidated report
            markdown_path, timestamp = self._create_consolidated_report(report_text, linkedin_content)
            
            if markdown_path:
                logger.info(f"Consolidated report markdown generated at {markdown_path}")
                
                # Step 4: Create HTML version for easier viewing
                html_path = self._create_html_version(markdown_path)
                if html_path:
                    logger.info(f"HTML version generated at {html_path}")
                    
                    # Step 5: Create PDF version (report only, no LinkedIn posts)
                    pdf_path = self._create_pdf_version(html_path)
                    if pdf_path:
                        logger.info(f"PDF version generated at {pdf_path}")
                    else:
                        logger.warning("Failed to generate PDF version")
                else:
                    logger.warning("Failed to generate HTML version")
            else:
                logger.error("Failed to generate consolidated report markdown")
                
            return markdown_path, html_path, pdf_path
            
        except Exception as e:
            logger.error(f"Error generating consolidated report: {e}")
            return None, None, None
    
    def _create_consolidated_report(self, daily_report, linkedin_posts):
        """Create a consolidated markdown report with daily report and LinkedIn posts."""
        try:
            # Create timestamp for report filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Get current date formatted for display
            current_date = datetime.now().strftime("%B %d, %Y")
            current_time = datetime.now().strftime("%I:%M %p")
            
            # Create report dir
            os.makedirs(self.reports_dir, exist_ok=True)
            
            # Generate the report file path
            report_path = os.path.join(self.reports_dir, f"consolidated_report_{timestamp}.md")
            
            # Write the report
            with open(report_path, 'w', encoding='utf-8') as f:
                # Write title
                f.write(f"# Business Intelligence Report: {current_date}\n\n")
                
                # Add client information
                f.write(f"**Prepared for:** {self.client_name}\n\n")
                
                # Add report frequency
                f.write(f"**Report type:** {self.report_frequency.capitalize()}\n\n")
                
                # Add timestamp and report ID
                f.write(f"**Generated:** {current_date} at {current_time} | **Report ID:** {timestamp}\n\n")
                
                # Add Table of Contents
                f.write("## Table of Contents\n\n")
                f.write("1. [Business Intelligence Report](#business-intelligence-report)\n")
                if linkedin_posts and self.include_linkedin:
                    f.write("2. [LinkedIn Posts](#linkedin-posts)\n")
                f.write("\n")
                
                # Add horizontal ruler
                f.write("---\n\n")
                
                # Write Daily Report Section
                f.write("## Business Intelligence Report\n\n")
                f.write(daily_report)
                f.write("\n\n")
                
                # Add LinkedIn Posts Section if available
                if linkedin_posts:
                    f.write("## LinkedIn Posts\n\n")
                    f.write(linkedin_posts)
                    f.write("\n\n")
                
                # Add footer
                f.write("---\n\n")
                f.write(f"*© Global Possibilities. Report generated on {current_date} at {current_time}.*\n")
            
            return report_path, timestamp
            
        except Exception as e:
            logger.error(f"Error creating consolidated report: {e}")
            return None, None
    
    def _create_html_version(self, markdown_path):
        """Create an HTML version of the report with optional chatbot."""
        try:
            # Check if the markdown file exists
            if not os.path.exists(markdown_path):
                logger.error(f"Markdown file not found: {markdown_path}")
                return None
            
            # Read the markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
            
            # Convert markdown to HTML
            html_content = markdown.markdown(markdown_content, extensions=['tables', 'fenced_code'])
            
            # Get timestamp from filename
            filename = os.path.basename(markdown_path)
            match = re.search(r'consolidated_report_(\d{8}_\d{6})\.md', filename)
            timestamp = match.group(1) if match else datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Parse the date from timestamp
            try:
                date_obj = datetime.strptime(timestamp, "%Y%m%d_%H%M%S")
                formatted_date = date_obj.strftime("%B %d, %Y")
                formatted_time = date_obj.strftime("%I:%M %p")
            except:
                formatted_date = "Unknown Date"
                formatted_time = "Unknown Time"
            
            # Create output HTML file path
            html_path = markdown_path.replace('.md', '.html')
            
            # Create assets directory if it doesn't exist
            assets_dir = os.path.join(os.path.dirname(html_path), 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            
            # Get default CSS
            css_content = self._get_default_css()
            
            # Create CSS file
            css_path = os.path.join(assets_dir, 'report.css')
            with open(css_path, 'w', encoding='utf-8') as f:
                f.write(css_content)
            
            # Parse HTML with BeautifulSoup for further manipulation
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find headings that look like article headlines and add hyperlinks if possible
            headings = soup.find_all(['h2', 'h3', 'h4'])
            for heading in headings:
                # Skip section headings like "Business Intelligence Report" and "LinkedIn Posts"
                if heading.text.strip() in ["Business Intelligence Report", "LinkedIn Posts"]:
                    continue
                
                # Check if there's a URL in the elements after this heading
                next_elements = []
                current = heading.next_sibling
                for _ in range(5):  # Look at up to 5 elements after the heading
                    if current:
                        next_elements.append(current)
                        current = current.next_sibling
                    else:
                        break
                
                # Look for URLs in the text of these elements
                url_match = None
                for element in next_elements:
                    if hasattr(element, 'text'):
                        # Look for URL patterns in text
                        matches = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', element.text)
                        if matches:
                            url_match = matches[0]
                            if not url_match.startswith('http'):
                                url_match = 'https://' + url_match
                            break
                        # Look for "Source: example.com" pattern
                        source_match = re.search(r'Source[s]?:\s*([^\s<>",]+\.[^\s<>",]+)', element.text)
                        if source_match:
                            domain = source_match.group(1)
                            url_match = f"https://{domain}"
                            break
                
                # If a URL was found, wrap the heading in a link
                if url_match:
                    link = soup.new_tag('a', href=url_match, target='_blank')
                    # Move the contents of the heading to the link
                    link.contents = heading.contents
                    # Clear the heading and append the link
                    heading.clear()
                    heading.append(link)
            
            # Add the chatbot if needed
            chatbot_html = None
            if self.include_chatbot:
                chatbot_html = self._get_chatbot_html(timestamp)
            
            if chatbot_html:
                # Find the spot to insert chatbot - after LinkedIn Posts or at the end
                linkedin_heading = soup.find('h2', string='LinkedIn Posts')
                
                if linkedin_heading:
                    # Find the next h2 after LinkedIn Posts or the end of document
                    current = linkedin_heading
                    while current.next_sibling and current.name != 'h2':
                        current = current.next_sibling
                    
                    # Insert chatbot after LinkedIn section
                    chatbot_div = BeautifulSoup(chatbot_html, 'html.parser')
                    current.insert_after(chatbot_div)
                else:
                    # Add to the end of the document
                    chatbot_div = BeautifulSoup(chatbot_html, 'html.parser')
                    soup.append(chatbot_div)
            
            # Create a complete HTML document
            html_document = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Intelligence Report - {formatted_date}</title>
    <link rel="stylesheet" href="assets/report.css">
</head>
<body>
    <div class="report-container">
        <header class="report-header">
            <h1>Business Intelligence Report</h1>
            <p class="report-meta">
                <span class="client-name">Prepared for: {self.client_name}</span> | 
                <span class="report-type">{self.report_frequency.capitalize()} Report</span> | 
                <span class="report-date">Generated on {formatted_date} at {formatted_time}</span>
            </p>
        </header>
        
        <div class="report-body">
            {soup.prettify()}
        </div>
        
        <footer class="report-footer">
            <p>&copy; {datetime.now().year} Global Possibilities - All Rights Reserved</p>
            <p>This report is confidential and intended solely for the use of the client named above.</p>
        </footer>
    </div>
</body>
</html>
"""
            
            # Write the HTML file
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_document)
            
            return html_path
        
        except Exception as e:
            logger.error(f"Error creating HTML version: {e}")
            return None
    
    def _is_wkhtmltopdf_available(self):
        """Check if wkhtmltopdf is available on the system."""
        try:
            result = subprocess.run(['wkhtmltopdf', '--version'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE,
                                   check=False)
            return result.returncode == 0
        except Exception:
            return False
    
    def _create_pdf_version(self, html_path):
        """Create a PDF version of the consolidated report (excluding the LinkedIn posts section)."""
        try:
            # Only proceed if wkhtmltopdf is available
            if not self._is_wkhtmltopdf_available():
                logger.warning("wkhtmltopdf not available. Skipping PDF generation.")
                return None
                
            # Get timestamp from filename
            base_name = os.path.basename(html_path)
            timestamp = base_name.replace('consolidated_report_', '').replace('.html', '')
            
            # Parse timestamp for display
            try:
                date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                formatted_date = date_obj.strftime('%B %d, %Y')
                formatted_time = date_obj.strftime('%I:%M %p')
            except:
                formatted_date = datetime.now().strftime('%B %d, %Y')
                formatted_time = datetime.now().strftime('%I:%M %p')
            
            # Load HTML and modify it to remove LinkedIn posts
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
                
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find and remove LinkedIn section - look for heading containing "LinkedIn"
            linkedin_headers = soup.find_all(['h1', 'h2', 'h3'], string=lambda text: text and 'LinkedIn' in text)
            for header in linkedin_headers:
                # Find the next header of same or higher level
                current_tag = header.name
                level = int(current_tag[1])
                
                # Get all siblings after this header until we find another header of same or higher level
                # or until the end of the document
                next_node = header.find_next_sibling()
                nodes_to_remove = [header]
                
                while next_node:
                    if next_node.name in ['h1', 'h2', 'h3'] and int(next_node.name[1]) <= level:
                        break
                    nodes_to_remove.append(next_node)
                    next_node = next_node.find_next_sibling()
                    
                for node in nodes_to_remove:
                    node.decompose()
            
            # Update the header to include timestamp information
            if soup.head and soup.head.title:
                soup.head.title.string = f"Business Intelligence Report - {formatted_date}"
            
            # Add or update the timestamp in the report header
            report_header = soup.find('div', class_='report-header')
            if report_header:
                timestamp_div = report_header.find('div', class_='timestamp')
                if timestamp_div:
                    timestamp_div.clear()
                    timestamp_div.append(soup.new_tag('div'))
                    timestamp_div.div.string = f"Generated: {formatted_date}"
                    
                    time_div = soup.new_tag('div')
                    time_div.string = f"Time: {formatted_time}"
                    timestamp_div.append(time_div)
                    
                    id_div = soup.new_tag('div')
                    id_div.string = f"Report ID: {timestamp}"
                    timestamp_div.append(id_div)
            
            # Update footer timestamp
            footer = soup.find('footer')
            if footer:
                p_tags = footer.find_all('p')
                if len(p_tags) > 1:
                    p_tags[1].string = f"Report generated on {formatted_date} at {formatted_time}"
                    
            # Save the modified HTML to a temporary file
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                temp_html_path = temp_html.name
                temp_html.write(soup.prettify().encode('utf-8'))
                
            # Create PDF output path
            pdf_path = html_path.replace('.html', '.pdf')
            
            # Generate the PDF
            subprocess.run([
                'wkhtmltopdf',
                '--enable-local-file-access',
                '--footer-center', f'Page [page] of [topage] | © Global Possibilities | Generated: {formatted_date}',
                '--footer-font-size', '8',
                '--margin-bottom', '20',
                '--margin-top', '20',
                '--margin-left', '20',
                '--margin-right', '20',
                temp_html_path,
                pdf_path
            ], check=True)
            
            # Remove temporary HTML file
            os.unlink(temp_html_path)
            
            return pdf_path
            
        except Exception as e:
            logger.error(f"Error creating PDF version: {e}")
            return None

    def _format_linkedin_posts(self, linkedin_posts):
        """Format LinkedIn posts list into a markdown string."""
        if not linkedin_posts or not isinstance(linkedin_posts, list):
            return None
            
        try:
            formatted_content = []
            
            # Intro text
            formatted_content.append("The following LinkedIn posts have been generated based on the business intelligence report:\n")
            
            # Format each post
            for i, post in enumerate(linkedin_posts):
                if isinstance(post, dict):
                    title = post.get('title', f'Business Insight {i+1}')
                    content = post.get('content', '')
                    category = post.get('category', 'general')
                    
                    formatted_content.append(f"### Post {i+1}: {title}")
                    formatted_content.append(f"**Category:** {category.replace('_', ' ').title()}")
                    formatted_content.append("```")
                    formatted_content.append(content)
                    formatted_content.append("```")
                    formatted_content.append("")  # Empty line
            
            return "\n".join(formatted_content)
            
        except Exception as e:
            logger.error(f"Error formatting LinkedIn posts: {e}")
            return None

    def _get_default_css(self):
        """Get the default CSS styling for the HTML report."""
        return """
/* Global Possibilities Business Intelligence Report Styling */
:root {
    --primary-color: #2c3e50;
    --accent-color: #3498db;
    --bg-color: #ffffff;
    --text-color: #333333;
    --light-bg: #f8f9fa;
    --border-color: #ddd;
    --success-color: #27ae60;
    --warning-color: #f39c12;
    --danger-color: #e74c3c;
    --font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
}

/* Base Styles */
body {
    font-family: var(--font-family);
    line-height: 1.6;
    color: var(--text-color);
    background-color: var(--light-bg);
    margin: 0;
    padding: 0;
}

.report-container {
    max-width: 1200px;
    margin: 0 auto;
    background-color: var(--bg-color);
    box-shadow: 0 0 15px rgba(0, 0, 0, 0.1);
}

/* Header Styles */
.report-header {
    background-color: var(--primary-color);
    color: white;
    padding: 2rem;
    position: relative;
}

.header-content {
    display: flex;
    align-items: center;
    gap: 1.5rem;
}

.logo {
    max-height: 80px;
    max-width: 200px;
}

.header-text h1 {
    margin: 0;
    padding: 0;
    font-size: 2.2rem;
    font-weight: 700;
}

.date-badge {
    display: inline-block;
    background-color: rgba(255, 255, 255, 0.2);
    padding: 0.3rem 0.8rem;
    border-radius: 50px;
    font-size: 0.9rem;
    margin-top: 0.5rem;
}

/* Report Body */
.report-body {
    padding: 2rem;
    min-height: 70vh;
}

/* Typography */
h1, h2, h3, h4, h5, h6 {
    color: var(--primary-color);
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
    line-height: 1.3;
}

h1 {
    font-size: 2.2rem;
    border-bottom: 2px solid var(--accent-color);
    padding-bottom: 0.3em;
}

h2 {
    font-size: 1.8rem;
    border-bottom: 1px solid var(--border-color);
    padding-bottom: 0.2em;
}

h3 {
    font-size: 1.5rem;
}

h4 {
    font-size: 1.3rem;
}

p {
    margin: 1em 0;
}

a {
    color: var(--accent-color);
    text-decoration: none;
    transition: color 0.2s ease;
}

a:hover {
    color: #1d6fa5;
    text-decoration: underline;
}

/* Table Styles */
table {
    border-collapse: collapse;
    width: 100%;
    margin: 1.5em 0;
    overflow-x: auto;
    display: block;
}

@media (min-width: 768px) {
    table {
        display: table;
    }
}

th, td {
    border: 1px solid var(--border-color);
    padding: 0.75rem;
    text-align: left;
}

th {
    background-color: var(--light-bg);
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #f9f9f9;
}

/* Code Blocks */
pre {
    background-color: var(--light-bg);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    padding: 1em;
    overflow-x: auto;
    margin: 1.5em 0;
}

code {
    font-family: 'Consolas', 'Monaco', 'Andale Mono', monospace;
    font-size: 0.9em;
    background-color: var(--light-bg);
    padding: 0.2em 0.4em;
    border-radius: 3px;
}

/* Lists */
ul, ol {
    margin: 1em 0;
    padding-left: 2em;
}

li {
    margin-bottom: 0.5em;
}

/* Blockquotes */
blockquote {
    border-left: 4px solid var(--accent-color);
    margin: 1.5em 0;
    padding: 0.5em 1em;
    color: #555;
    background-color: #f9f9f9;
}

/* Horizontal Rule */
hr {
    border: 0;
    border-top: 1px solid var(--border-color);
    margin: 2em 0;
}

/* Links in Headings */
h2 a, h3 a, h4 a {
    color: inherit;
    text-decoration: none;
    position: relative;
    display: inline-block;
    width: 100%;
}

h2 a:hover, h3 a:hover, h4 a:hover {
    color: var(--accent-color);
}

h2 a::after, h3 a::after, h4 a::after {
    content: "🔗";
    font-size: 0.8em;
    margin-left: 8px;
    opacity: 0.6;
    vertical-align: middle;
}

/* Footer */
.report-footer {
    background-color: var(--primary-color);
    color: rgba(255, 255, 255, 0.7);
    text-align: center;
    padding: 1.5rem;
    font-size: 0.9rem;
}

.report-footer p {
    margin: 0;
}

/* Chatbot Container */
.chatbot-container {
    margin-top: 3rem;
    padding: 1.5rem;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background-color: var(--light-bg);
}

.chatbot-header {
    display: flex;
    align-items: center;
    margin-bottom: 1rem;
}

.chatbot-header h3 {
    margin: 0;
    color: var(--primary-color);
}

.chatbot-icon {
    margin-right: 0.8rem;
    color: var(--accent-color);
    font-size: 1.5rem;
}

.chat-interface {
    background-color: white;
    border-radius: 8px;
    padding: 1rem;
    min-height: 300px;
}

.chat-input-container {
    display: flex;
    margin-top: 1rem;
}

.chat-input {
    flex: 1;
    padding: 0.8rem;
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: inherit;
}

.chat-send-btn {
    background-color: var(--accent-color);
    color: white;
    border: none;
    padding: 0 1.2rem;
    margin-left: 0.5rem;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s ease;
}

.chat-send-btn:hover {
    background-color: #2980b9;
}

/* Print Styles */
@media print {
    body {
        background-color: white;
    }
    
    .report-container {
        box-shadow: none;
        max-width: 100%;
    }
    
    .report-header {
        background-color: white !important;
        color: black !important;
        padding: 1rem 0;
    }
    
    .date-badge {
        background-color: #f1f1f1;
        color: black;
    }
    
    .chatbot-container {
        display: none;
    }
    
    a {
        text-decoration: none !important;
        color: black !important;
    }
    
    h2 a::after, h3 a::after, h4 a::after {
        content: "";
    }
    
    .report-footer {
        background-color: white !important;
        color: black !important;
        border-top: 1px solid #eee;
        padding: 1rem 0;
    }
}
"""

    def _get_chatbot_html(self, timestamp):
        """Get the HTML for the interactive chatbot."""
        # Check if OpenAI API key is set and chatbot is enabled
        if not os.getenv('OPENAI_API_KEY') or not self.include_chatbot:
            return None
        
        # Only include chatbot in HTML version, not PDF
        chatbot_html = f"""
        <div class="chatbot-container">
            <div class="chatbot-header">
                <div class="chatbot-icon">💬</div>
                <h3>Business Intelligence Assistant</h3>
            </div>
            <p>Ask questions about this report or request additional insights about GCC business trends.</p>
            <div class="chat-interface" id="chat-messages">
                <div id="welcome-message" style="color: #666; margin-bottom: 15px;">
                    <strong>Assistant:</strong> Hello! I can answer questions about this business intelligence report
                    and provide additional insights about GCC markets. What would you like to know?
                </div>
            </div>
            <div class="chat-input-container">
                <input type="text" id="chat-input" class="chat-input" placeholder="Type your question here..." />
                <button id="chat-send" class="chat-send-btn">Send</button>
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const chatMessages = document.getElementById('chat-messages');
            const chatInput = document.getElementById('chat-input');
            const chatSendBtn = document.getElementById('chat-send');
            
            // Store report content
            const reportContent = document.querySelector('.report-body').innerText;
            
            // Function to add a message to the chat
            function addMessage(sender, message) {{
                const msgDiv = document.createElement('div');
                msgDiv.style.marginBottom = '10px';
                
                if (sender === 'user') {{
                    msgDiv.innerHTML = '<strong>You:</strong> ' + message;
                    msgDiv.style.textAlign = 'right';
                    msgDiv.style.color = '#2c3e50';
                }} else {{
                    msgDiv.innerHTML = '<strong>Assistant:</strong> ' + message;
                    msgDiv.style.color = '#333';
                }}
                
                chatMessages.appendChild(msgDiv);
                
                // Scroll to bottom
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }}
            
            // Function to send a message
            function sendMessage() {{
                const message = chatInput.value.trim();
                if (!message) return;
                
                // Add user message
                addMessage('user', message);
                
                // Clear input
                chatInput.value = '';
                
                // Add loading indicator
                const loadingDiv = document.createElement('div');
                loadingDiv.id = 'loading-indicator';
                loadingDiv.innerHTML = '<strong>Assistant:</strong> <em>Thinking...</em>';
                loadingDiv.style.color = '#999';
                chatMessages.appendChild(loadingDiv);
                
                // Make API call
                fetch('/api/chat', {{
                    method: 'POST',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{
                        message: message,
                        report_content: reportContent,
                        client_name: '{self.client_name}',
                        report_type: '{self.report_frequency}',
                        report_id: '{timestamp}'
                    }})
                }})
                .then(response => response.json())
                .then(data => {{
                    // Remove loading indicator
                    const loadingIndicator = document.getElementById('loading-indicator');
                    if (loadingIndicator) {{
                        loadingIndicator.remove();
                    }}
                    
                    if (data.error) {{
                        addMessage('assistant', 'Error: ' + data.error);
                    }} else {{
                        addMessage('assistant', data.reply);
                    }}
                }})
                .catch(error => {{
                    // Remove loading indicator
                    const loadingIndicator = document.getElementById('loading-indicator');
                    if (loadingIndicator) {{
                        loadingIndicator.remove();
                    }}
                    
                    console.error('Error:', error);
                    addMessage('assistant', 'Sorry, there was an error processing your request. Please try again.');
                }});
            }}
            
            // Event listeners
            chatSendBtn.addEventListener('click', sendMessage);
            
            chatInput.addEventListener('keypress', function(e) {{
                if (e.key === 'Enter') {{
                    sendMessage();
                }}
            }});
        }});
        </script>
        """
        
        return chatbot_html

if __name__ == "__main__":
    # Enable full standalone test without dependencies
    STANDALONE_TEST = True
    
    # Simple test data
    test_report = """# UAE Business Intelligence Report

## Economic Insights

The UAE economy continues to show resilience despite global challenges. Key sectors such as real estate, tourism, and technology are experiencing growth.

### Key Economic Indicators
- GDP Growth: 3.8%
- Inflation: 2.1%
- Foreign Direct Investment: Increased by 14% year-over-year

## Industry Developments

### Technology
The UAE is rapidly becoming a technology hub in the Middle East, with Dubai's Internet City attracting major global players. Recent government initiatives support AI development and blockchain implementation.

### Real Estate
Property transactions in Dubai increased by 12% in the last quarter, showing strong market activity despite global economic concerns.

### Energy
The UAE continues to diversify its energy portfolio, with significant investments in renewable energy projects, particularly solar power.

## US-UAE Relations

Bilateral trade between the US and UAE reached $24.5 billion in the past year, with significant growth in sectors such as defense, technology, and healthcare.

Key partnerships announced this week:
1. A major US healthcare provider expanding operations in Abu Dhabi
2. Technology transfer agreement in AI research
3. Joint venture in sustainable agriculture technologies

## Regulatory Updates

The UAE government announced new regulations to streamline business licensing processes, reducing processing time by 40% for new business applications.

## Market Opportunities

Emerging opportunities exist in:
- Green technologies and sustainability solutions
- Healthcare technology and telemedicine
- Financial technology, particularly in payment solutions
- E-commerce platforms targeting the GCC region
"""

    # Test LinkedIn posts
    test_linkedin_posts = [
        {
            "title": "UAE Economic Resilience",
            "content": """📈 **UAE Economy Shows Remarkable Resilience**

Despite global economic headwinds, the UAE economy continues to demonstrate impressive resilience with 3.8% GDP growth and controlled inflation at 2.1%.

Key sectors driving this growth include real estate, tourism, and technology, with property transactions in Dubai alone increasing by 12% in the last quarter.

Foreign direct investment has surged by 14% year-over-year, reflecting strong international confidence in the UAE's economic future.

What factors do you think contribute most to the UAE's economic stability in these uncertain times?

#UAEEconomy #EconomicGrowth #BusinessIntelligence #InvestmentOpportunities #GlobalBusiness""",
            "category": "economy"
        },
        {
            "title": "US-UAE Partnership Growth",
            "content": """🇺🇸🇦🇪 **US-UAE Business Relations Reach New Heights**

Bilateral trade between the US and UAE has now reached $24.5 billion, with significant growth across defense, technology, and healthcare sectors.

This week saw major partnership announcements including US healthcare expansion in Abu Dhabi, technology transfer in AI research, and innovative joint ventures in sustainable agriculture.

These partnerships demonstrate the deepening economic ties between our nations and create substantial opportunities for businesses on both sides.

How might your organization benefit from the growing US-UAE business ecosystem?

#USUAERelations #InternationalTrade #BusinessPartnerships #GlobalOpportunities #MiddleEastBusiness""",
            "category": "us_uae_relations"
        }
    ]

    # Configure a standalone test directory for reports
    if STANDALONE_TEST:
        # Create a test directory in the current location
        test_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_reports")
        print(f"Creating test directory at: {test_dir}")
        os.makedirs(test_dir, exist_ok=True)
        
        # Create a standalone instance with the test directory
        generator = ConsolidatedReportGenerator(reports_dir=test_dir, standalone_mode=True)
    else:
        # Use default configurations
        generator = ConsolidatedReportGenerator()
    
    # Generate the report
    md_path, html_path, pdf_path = generator.generate(test_report, test_linkedin_posts)
    
    # Report results
    if md_path:
        print(f"Markdown report generated at: {md_path}")
        if html_path:
            print(f"HTML report generated at: {html_path}")
        if pdf_path:
            print(f"PDF report generated at: {pdf_path}")
        
        # Provide instructions for viewing
        print("\nTo view the HTML report, open it in your browser:")
        print(f"open {html_path}")
    else:
        print("Failed to generate consolidated report.") 