import os
import sys
import json
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

# Define paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
CLIENTS_CONFIG_DIR = os.path.join(CONFIG_DIR, 'clients')

# Ensure required directories exist
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(CLIENTS_CONFIG_DIR, exist_ok=True)

# Define available report frequencies
FREQUENCIES = ["daily", "weekly", "monthly", "quarterly"]

def load_client_config(client_id):
    """Load the configuration for a specific client."""
    try:
        config_path = os.path.join(CLIENTS_CONFIG_DIR, f"{client_id}.json")
        if not os.path.exists(config_path):
            logger.warning(f"Config for client '{client_id}' not found at {config_path}")
            # Fallback to general if specific client config doesn't exist
            config_path = os.path.join(CLIENTS_CONFIG_DIR, "general.json")
            
        with open(config_path, 'r') as f:
            config = json.load(f)
            return config
    except Exception as e:
        logger.error(f"Error loading client config for '{client_id}': {e}")
        return {
            "name": "Global Possibilities Team",
            "description": "Internal team report",
            "include_linkedin": True,
            "include_chatbot": True,
            "keywords": []
        }

def get_available_clients():
    """Get a list of available clients based on config files."""
    try:
        if not os.path.exists(CLIENTS_CONFIG_DIR):
            return ["general"]
            
        clients = []
        for filename in os.listdir(CLIENTS_CONFIG_DIR):
            if filename.endswith('.json'):
                client_id = filename.replace('.json', '')
                clients.append(client_id)
        
        # Ensure "general" is always available
        if "general" not in clients and os.path.exists(os.path.join(CLIENTS_CONFIG_DIR, "general.json")):
            clients.append("general")
            
        return clients if clients else ["general"]
    except Exception as e:
        logger.error(f"Error getting available clients: {e}")
        return ["general"]

def run_collection(client_config, frequency="daily"):
    """Run the news collection process with client-specific settings."""
    logger.info("Starting news collection process...")
    
    # Get frequency-specific settings
    report_type_config = client_config.get("report_types", {}).get(frequency, {})
    days_back = report_type_config.get("days_back", 1)
    limit_per_source = report_type_config.get("articles_limit", 25) // 5  # Divide by estimated number of sources
    
    # Get client keywords
    keywords = client_config.get("keywords", [])
    
    # Initialize the collector
    collector = GCCBusinessNewsCollector()
    
    # Collect news with client-specific settings
    if keywords:
        logger.info(f"Focusing collection on {len(keywords)} keywords")
        articles = collector.collect_news(
            days_back=days_back,
            limit_per_source=limit_per_source,
            focus_keywords=keywords
        )
    else:
        articles = collector.collect_news(
            days_back=days_back,
            limit_per_source=limit_per_source
        )
    
    if articles:
        logger.info(f"Successfully collected {len(articles)} articles.")
        return articles
    else:
        logger.warning("No articles were collected.")
        return []

def run_report_generation(articles=None, client="general", frequency="daily"):
    """Run the report generation process."""
    logger.info(f"Starting report generation process for client: {client}, frequency: {frequency}...")
    
    # Load client configuration
    client_config = load_client_config(client)
    client_name = client_config.get("name", "Global Possibilities Team")
    include_linkedin = client_config.get("include_linkedin", True)
    include_chatbot = client_config.get("include_chatbot", True)
    
    # Create the client-specific directory if it doesn't exist
    client_reports_dir = os.path.join(REPORTS_DIR, client, frequency)
    os.makedirs(client_reports_dir, exist_ok=True)
    
    # Initialize the report generator with client-specific settings
    generator = ConsolidatedReportGenerator(
        reports_dir=client_reports_dir,
        client_name=client_name,
        report_frequency=frequency,
        include_linkedin=include_linkedin,
        include_chatbot=include_chatbot
    )
    
    # Generate the consolidated report
    md_path, html_path, pdf_path = generator.generate_all(articles)
    
    if md_path:
        logger.info(f"Successfully generated report at {md_path}")
        if html_path:
            logger.info(f"HTML version available at {html_path}")
        if pdf_path:
            logger.info(f"PDF version available at {pdf_path}")
        return md_path, html_path, pdf_path
    else:
        logger.error("Failed to generate report.")
        return None, None, None

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
    # Get available clients
    available_clients = get_available_clients()
    
    parser = argparse.ArgumentParser(description='Run the GCC Business Intelligence Platform manually.')
    parser.add_argument('--skip-collection', action='store_true', help='Skip the news collection process and use existing data.')
    parser.add_argument('--skip-report', action='store_true', help='Skip the report generation process.')
    parser.add_argument('--no-browser', action='store_true', help='Do not automatically open the report in a browser.')
    parser.add_argument('--open-latest', action='store_true', help='Open the latest report in browser without running collection.')
    parser.add_argument('--client', type=str, choices=available_clients, default='general',
                      help=f'Generate a report for a specific client. Default is general.')
    parser.add_argument('--frequency', type=str, choices=FREQUENCIES, default='daily',
                      help='Report frequency: daily, weekly, monthly, or quarterly. Default is daily.')
    args = parser.parse_args()
    
    # Handle the open-latest option separately
    if args.open_latest:
        try:
            report_dir = os.path.join(REPORTS_DIR, args.client, args.frequency)
            
            if not os.path.exists(report_dir):
                logger.error(f"No reports directory found for {args.client} ({args.frequency}).")
                return
            
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
    
    # Load client config
    client_config = load_client_config(args.client)
    
    start_time = datetime.now()
    logger.info(f"Starting manual run at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Client: {client_config.get('name')} ({args.client}), Frequency: {args.frequency}")
    
    try:
        # Step 1: Collect news if not skipped
        articles = None
        if not args.skip_collection:
            articles = run_collection(client_config, args.frequency)
        else:
            logger.info("Skipping news collection process as requested.")
        
        # Step 2: Generate reports if not skipped
        html_path = None
        pdf_path = None
        if not args.skip_report:
            md_path, html_path, pdf_path = run_report_generation(
                articles, 
                client=args.client,
                frequency=args.frequency
            )
            
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
            if pdf_path:
                print(f"📑 PDF Report: {pdf_path}")
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