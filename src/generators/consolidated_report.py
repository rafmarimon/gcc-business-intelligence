import os
import logging
import json
from datetime import datetime
from pathlib import Path
import markdown
from dotenv import load_dotenv
import shutil

# Import our modules
from processors.news_analyzer import GCCBusinessNewsAnalyzer
from generators.linkedin_content import LinkedInContentGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConsolidatedReport")

class ConsolidatedReportGenerator:
    """
    Generates a consolidated report containing weekly business intelligence and LinkedIn posts.
    """
    def __init__(self, reports_dir='reports', content_dir='content', data_dir='data'):
        """Initialize the consolidated report generator."""
        self.reports_dir = reports_dir
        self.content_dir = content_dir
        self.data_dir = data_dir
        
        # Create directories if they don't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.content_dir, exist_ok=True)
        
        # Initialize components
        self.analyzer = GCCBusinessNewsAnalyzer(
            reports_dir=self.reports_dir,
            data_dir=self.data_dir
        )
        self.linkedin_generator = LinkedInContentGenerator(
            reports_dir=self.reports_dir,
            content_dir=self.content_dir,
            data_dir=self.data_dir
        )
    
    def generate_all(self, articles=None):
        """Generate the complete report: weekly analysis and LinkedIn posts."""
        logger.info("Starting consolidated report generation...")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Step 1: Generate the weekly report
        logger.info("Generating weekly business intelligence report...")
        report_path, report_text = self.analyzer.generate_weekly_report(articles)
        
        if not report_path or not report_text:
            logger.error("Failed to generate weekly report.")
            return None
        
        logger.info(f"Weekly report generated at {report_path}")
        
        # Step 2: Generate LinkedIn posts based on the report
        logger.info("Generating LinkedIn posts...")
        linkedin_posts = self.linkedin_generator.generate_linkedin_posts()
        
        if not linkedin_posts:
            logger.warning("No LinkedIn posts were generated.")
        else:
            logger.info(f"Generated {len(linkedin_posts)} LinkedIn posts")
        
        # Step 3: Create the consolidated report
        consolidated_path = self._create_consolidated_report(report_text, linkedin_posts, timestamp)
        
        if consolidated_path:
            logger.info(f"Consolidated report generated at {consolidated_path}")
            
            # Create HTML version for better viewing
            html_path = self._create_html_version(consolidated_path)
            if html_path:
                logger.info(f"HTML version generated at {html_path}")
                return consolidated_path, html_path
            
            return consolidated_path, None
        
        logger.error("Failed to generate consolidated report.")
        return None, None
    
    def _create_consolidated_report(self, report_text, linkedin_posts, timestamp):
        """Combine the weekly report and LinkedIn posts into a single markdown file."""
        try:
            file_path = os.path.join(self.reports_dir, f"consolidated_report_{timestamp}.md")
            
            with open(file_path, 'w', encoding='utf-8') as f:
                # Write the title
                f.write("# UAE/GCC Business Intelligence: Weekly Report & LinkedIn Content\n\n")
                f.write(f"**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("---\n\n")
                
                # Add table of contents
                f.write("## Table of Contents\n\n")
                f.write("1. [Weekly Business Intelligence Report](#weekly-business-intelligence-report)\n")
                if linkedin_posts:
                    f.write("2. [LinkedIn Content](#linkedin-content)\n")
                f.write("\n---\n\n")
                
                # Add the weekly report
                f.write("## Weekly Business Intelligence Report\n\n")
                f.write(report_text)
                f.write("\n\n---\n\n")
                
                # Add LinkedIn posts if available
                if linkedin_posts:
                    f.write("## LinkedIn Content\n\n")
                    f.write("The following LinkedIn posts have been generated based on the business intelligence report:\n\n")
                    
                    for i, post in enumerate(linkedin_posts):
                        f.write(f"### Post {i+1}: {post.get('title', 'Business Insight')}\n\n")
                        f.write(f"```\n{post.get('content', '')}\n```\n\n")
                
                # Add footer
                f.write("\n\n---\n\n")
                f.write("*© Global Possibilities. All rights reserved.*\n")
            
            return file_path
            
        except Exception as e:
            logger.error(f"Error creating consolidated report: {e}")
            return None
    
    def _create_html_version(self, markdown_path):
        """Create an HTML version of the consolidated report for easier viewing."""
        try:
            # Read the markdown content
            with open(markdown_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Convert to HTML
            html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
            
            # Add CSS styling
            styled_html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>UAE/GCC Business Intelligence Report</title>
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        max-width: 900px;
                        margin: 0 auto;
                        padding: 20px;
                        color: #333;
                    }}
                    h1, h2, h3, h4, h5, h6 {{
                        color: #0078d4;
                        margin-top: 1.5em;
                        margin-bottom: 0.5em;
                    }}
                    h1 {{
                        text-align: center;
                        border-bottom: 2px solid #0078d4;
                        padding-bottom: 10px;
                    }}
                    hr {{
                        border: 1px solid #eee;
                        margin: 20px 0;
                    }}
                    pre {{
                        background-color: #f8f8f8;
                        border: 1px solid #ddd;
                        border-radius: 5px;
                        padding: 15px;
                        overflow-x: auto;
                    }}
                    code {{
                        font-family: 'Courier New', Courier, monospace;
                    }}
                    blockquote {{
                        border-left: 4px solid #0078d4;
                        padding-left: 15px;
                        margin-left: 0;
                        color: #555;
                    }}
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                    }}
                    table, th, td {{
                        border: 1px solid #ddd;
                    }}
                    th, td {{
                        padding: 12px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                    img {{
                        max-width: 100%;
                        height: auto;
                    }}
                    a {{
                        color: #0078d4;
                        text-decoration: none;
                    }}
                    a:hover {{
                        text-decoration: underline;
                    }}
                    .footer {{
                        text-align: center;
                        margin-top: 40px;
                        font-size: 0.9em;
                        color: #777;
                    }}
                </style>
            </head>
            <body>
                {html_content}
                <div class="footer">
                    <p>Generated by Global Possibilities Business Intelligence Platform</p>
                </div>
            </body>
            </html>
            """
            
            # Save the HTML file
            html_path = markdown_path.replace('.md', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(styled_html)
            
            # Copy any images from reports directory to maintain references
            img_dir = os.path.join(os.path.dirname(html_path), 'images')
            os.makedirs(img_dir, exist_ok=True)
            
            # Check for keyword chart and copy it
            chart_path = os.path.join(self.reports_dir, 'keyword_analysis.png')
            if os.path.exists(chart_path):
                shutil.copy(chart_path, os.path.join(img_dir, 'keyword_analysis.png'))
            
            return html_path
            
        except Exception as e:
            logger.error(f"Error creating HTML version: {e}")
            return None


if __name__ == "__main__":
    # Test the consolidated report generator
    generator = ConsolidatedReportGenerator()
    md_path, html_path = generator.generate_all()
    
    if md_path:
        print(f"Consolidated report generated at {md_path}")
        if html_path:
            print(f"HTML version available at {html_path}")
    else:
        print("Failed to generate consolidated report.") 