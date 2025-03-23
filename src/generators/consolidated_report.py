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
    def __init__(self, reports_dir=None, standalone_mode=False):
        """Initialize the consolidated report generator."""
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
        
        # Only initialize analyzers and generators if not in standalone mode
        if not standalone_mode:
            try:
                self.analyzer = GCCBusinessNewsAnalyzer(
                    config_file='config.json',
                    model='gpt-4o'
                )
                
                self.linkedin_generator = LinkedInContentGenerator(
                    config_file='config.json',
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
        logger.info(f"Standalone mode: {standalone_mode}")
    
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
                
                # Add timestamp and report ID
                f.write(f"**Generated:** {current_date} at {current_time} | **Report ID:** {timestamp}\n\n")
                
                # Add Table of Contents
                f.write("## Table of Contents\n\n")
                f.write("1. [Business Intelligence Report](#business-intelligence-report)\n")
                f.write("2. [LinkedIn Posts](#linkedin-posts)\n\n")
                
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
        """Create an HTML version of the consolidated report for easier viewing."""
        try:
            # Read the markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code', 'nl2br'])
            
            # Get the timestamp from the filename
            base_name = os.path.basename(markdown_path)
            timestamp = base_name.replace('consolidated_report_', '').replace('.md', '')
            
            # Parse timestamp for display
            try:
                date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                formatted_date = date_obj.strftime('%B %d, %Y')
                formatted_time = date_obj.strftime('%I:%M %p')
            except:
                formatted_date = datetime.now().strftime('%B %d, %Y')
                formatted_time = datetime.now().strftime('%I:%M %p')
                
            # Create output path
            html_path = markdown_path.replace('.md', '.html')
            
            # Create HTML document
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Business Intelligence Report - {formatted_date}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            color: #2c3e50;
            margin-top: 1.5em;
        }}
        
        h1 {{
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        
        h2 {{
            border-bottom: 1px solid #ddd;
            padding-bottom: 5px;
        }}
        
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        
        a:hover {{
            text-decoration: underline;
        }}
        
        pre {{
            background-color: #f8f9fa;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            overflow-x: auto;
        }}
        
        code {{
            font-family: Consolas, Monaco, 'Andale Mono', monospace;
            background-color: #f8f9fa;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 20px 0;
        }}
        
        th, td {{
            border: 1px solid #ddd;
            padding: 8px 12px;
            text-align: left;
        }}
        
        th {{
            background-color: #f2f2f2;
        }}
        
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        
        blockquote {{
            border-left: 4px solid #3498db;
            margin-left: 0;
            padding-left: 20px;
            color: #555;
        }}
        
        hr {{
            border: 0;
            border-top: 1px solid #eee;
            margin: 30px 0;
        }}
        
        .report-header {{
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 15px;
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .timestamp {{
            font-size: 0.9em;
            color: #6c757d;
            text-align: right;
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <div>
            <h1>Business Intelligence Report</h1>
            <p>Global Possibilities UAE/GCC Market Analysis</p>
        </div>
        <div class="timestamp">
            <div><strong>Generated:</strong> {formatted_date}</div>
            <div><strong>Time:</strong> {formatted_time}</div>
            <div><strong>Report ID:</strong> {timestamp}</div>
        </div>
    </div>
    
    {html_content}
    
    <footer style="margin-top: 50px; text-align: center; font-size: 0.8em; color: #6c757d;">
        <p>© Global Possibilities. All rights reserved.</p>
        <p>Report generated on {formatted_date} at {formatted_time}</p>
    </footer>
</body>
</html>""")
            
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