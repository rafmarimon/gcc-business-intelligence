import os
import sys
import logging
import argparse
import webbrowser
from datetime import datetime
from dotenv import load_dotenv

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our modules
from collectors.news_collector import GCCBusinessNewsCollector
from processors.news_analyzer import GCCBusinessNewsAnalyzer
from generators.linkedin_content import LinkedInContentGenerator
from generators.consolidated_report import ConsolidatedReportGenerator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("manual_run")

def run_collection():
    """Run the news collection process."""
    logger.info("Starting news collection process...")
    
    # Initialize the collector
    collector = GCCBusinessNewsCollector()
    
    # Collect news
    articles = collector.collect_news()
    
    if articles:
        logger.info(f"Successfully collected {len(articles)} articles.")
        return articles
    else:
        logger.warning("No articles were collected.")
        return []

def run_report_generation(articles=None):
    """Run the report generation process."""
    logger.info("Starting report generation process...")
    
    # Initialize the report generator
    generator = ConsolidatedReportGenerator()
    
    # Generate the consolidated report
    md_path, html_path = generator.generate_all(articles)
    
    if md_path:
        logger.info(f"Successfully generated report at {md_path}")
        if html_path:
            logger.info(f"HTML version available at {html_path}")
            return md_path, html_path
        return md_path, None
    else:
        logger.error("Failed to generate report.")
        return None, None

def open_report_in_browser(html_path):
    """Open the HTML report in the default browser."""
    if html_path and os.path.exists(html_path):
        try:
            logger.info(f"Opening report in browser: {html_path}")
            # Convert to a file URL
            file_url = f"file://{os.path.abspath(html_path)}"
            webbrowser.open_new_tab(file_url)
            return True
        except Exception as e:
            logger.error(f"Error opening report in browser: {e}")
            return False
    else:
        logger.warning("No HTML report available to open.")
        return False

def main():
    """Main function to run the entire process."""
    parser = argparse.ArgumentParser(description='Run the GCC Business Intelligence Platform manually.')
    parser.add_argument('--skip-collection', action='store_true', help='Skip the news collection process and use existing data.')
    parser.add_argument('--skip-report', action='store_true', help='Skip the report generation process.')
    parser.add_argument('--no-browser', action='store_true', help='Do not automatically open the report in a browser.')
    parser.add_argument('--open-latest', action='store_true', help='Open the latest report in browser without running collection.')
    args = parser.parse_args()
    
    # Handle the open-latest option separately
    if args.open_latest:
        try:
            report_dir = 'reports'
            html_files = [os.path.join(report_dir, f) for f in os.listdir(report_dir) 
                          if f.endswith('.html') and f.startswith('consolidated_report_')]
            
            if not html_files:
                logger.error("No reports found to open.")
                return
            
            # Get the most recent file
            latest_file = max(html_files, key=os.path.getctime)
            open_report_in_browser(latest_file)
            return
        except Exception as e:
            logger.error(f"Error opening latest report: {e}")
            return
    
    start_time = datetime.now()
    logger.info(f"Starting manual run at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Collect news if not skipped
        articles = None
        if not args.skip_collection:
            articles = run_collection()
        else:
            logger.info("Skipping news collection process as requested.")
        
        # Step 2: Generate reports if not skipped
        html_path = None
        if not args.skip_report:
            md_path, html_path = run_report_generation(articles)
            
            # Step 3: Open the report in a browser if requested
            if html_path and not args.no_browser:
                open_report_in_browser(html_path)
        else:
            logger.info("Skipping report generation process as requested.")
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Manual run completed in {duration.total_seconds():.2f} seconds.")
        
        # Show the result in a user-friendly format
        if html_path:
            print("\n" + "="*80)
            print("✅ Process completed successfully!")
            print(f"📊 HTML Report: {html_path}")
            if not args.no_browser:
                print("🌐 The report has been opened in your default browser.")
            print("="*80 + "\n")
    
    except KeyboardInterrupt:
        logger.info("Process interrupted by user.")
        print("\n❌ Process interrupted by user.")
    except Exception as e:
        logger.error(f"An error occurred during the manual run: {e}", exc_info=True)
        print(f"\n❌ Error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"An error occurred during the manual run: {e}", exc_info=True)
        sys.exit(1) 