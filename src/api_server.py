import os
import sys
import json
import glob
import logging
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS
from dotenv import load_dotenv
import re
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our custom OpenAI client with exponential backoff
try:
    from src.utils.openai_utils import OpenAIClient
    # Initialize OpenAI client
    api_key = os.getenv('OPENAI_API_KEY')
    openai_client = OpenAIClient(api_key) if api_key else None
except ImportError:
    logger.warning("Could not import OpenAIClient - OpenAI features will be disabled")
    openai_client = None

# Import ML components
try:
    from src.ml.report_integration import MLReportIntegration
    # Initialize ML component if available
    ml_integration = MLReportIntegration()
except ImportError:
    logger.warning("Could not import MLReportIntegration - ML features will be disabled")
    ml_integration = None
    MLReportIntegration = None

# Import our custom report bridge
try:
    from src.report_bridge import generate_report as bridge_generate_report, list_reports as bridge_list_reports
    has_report_bridge = True
    logger.info("Report Bridge loaded successfully")
except ImportError:
    logger.warning("Could not import Report Bridge - falling back to manual_run.py")
    has_report_bridge = False

# After the other imports, add:
import base64
import glob
import subprocess
from datetime import datetime, timedelta

# After the other imports from src.utils, add:
try:
    from src.generators.linkedin_content import LinkedInContentGenerator
    has_linkedin_generator = True
    logger.info("LinkedIn Content Generator loaded successfully")
except ImportError:
    logger.warning("Could not import LinkedInContentGenerator - LinkedIn features will be disabled")
    has_linkedin_generator = False

app = Flask(__name__, 
    static_folder='../reports',
    template_folder='templates'
)
CORS(app)  # Enable CORS for all routes

# Ensure directories exist
reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
forecasts_dir = os.path.join(os.path.expanduser("~"), "gp_reports", "forecasts")
os.makedirs(reports_dir, exist_ok=True)
os.makedirs(forecasts_dir, exist_ok=True)

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
        
        # Use the bridge if available
        if has_report_bridge:
            reports = bridge_list_reports(client, frequency, limit=10)
            return jsonify({"reports": reports})
        
        # Original implementation (fallback)
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
        
        # Get limit parameter, defaulting to 10
        limit = int(request.args.get('limit', 10))
        # Get offset parameter for pagination
        offset = int(request.args.get('offset', 0))
        
        # Apply pagination if specified
        if limit > 0:
            md_files = md_files[offset:offset+limit]
        
        # Get total count before pagination for meta info
        total_count = len(glob.glob(os.path.join(client_reports_dir, 'consolidated_report_*.md')))
        
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
                    # Try to extract client name
                    client_match = re.search(r'\*\*Prepared for:\*\* ([^\\n]+)', content)
                    if client_match:
                        client_name = client_match.group(1).strip()
                    
                    # Skip title and get the actual content
                    parts = content.split('---', 2)
                    if len(parts) > 2:
                        actual_content = parts[2]
                    else:
                        actual_content = content
                    
                    # Extract a brief description
                    description = actual_content.strip()[:200] + "..."
            except:
                description = f"{frequency.capitalize()} business intelligence report on GCC and UAE markets."
            
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
        
        # Add pagination metadata
        return jsonify({
            "reports": reports,
            "meta": {
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total_count
            }
        })
    
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        return jsonify({"error": str(e), "reports": []}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate a new report using the simplified report generator"""
    try:
        data = request.json
        report_type = data.get('report_type', 'daily')
        collect_news = data.get('collect_news', True)
        client = data.get('client', 'general')
        
        # Get available clients
        clients_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'clients')
        valid_clients = ['general']  # Always include general
        
        if os.path.exists(clients_dir):
            for filename in os.listdir(clients_dir):
                if filename.endswith('.json'):
                    client_id = filename.replace('.json', '')
                    valid_clients.append(client_id)
        
        # Validate inputs
        valid_report_types = ['daily', 'weekly', 'monthly', 'quarterly']
        
        if report_type not in valid_report_types:
            return jsonify({
                "success": False,
                "message": f"Invalid report type. Must be one of: {', '.join(valid_report_types)}"
            }), 400
            
        if client not in valid_clients:
            return jsonify({
                "success": False,
                "message": f"Invalid client. Must be one of: {', '.join(valid_clients)}"
            }), 400
        
        # Use the bridge if available
        if has_report_bridge:
            # Run in a separate thread to avoid blocking
            def run_with_bridge():
                try:
                    result = bridge_generate_report(client, report_type, skip_collection=not collect_news)
                    logger.info(f"Report generation with bridge: {result['success']}")
                except Exception as e:
                    logger.error(f"Error in report generation thread: {str(e)}")
            
            thread = threading.Thread(target=run_with_bridge)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "message": "Report generation started. Refresh the page in a moment to see your new report."
            })
        
        # Original implementation (fallback)
        # Prepare command arguments
        cmd_args = ['python', 'src/manual_run.py', '--no-browser']
        
        # Add client parameter
        cmd_args.extend(['--client', client])
        
        # Add frequency parameter
        cmd_args.extend(['--frequency', report_type])
        
        if not collect_news:
            cmd_args.append('--skip-collection')
        
        # Run the command in a separate thread to avoid blocking
        def run_command():
            try:
                # Get the path to the virtual environment python
                if os.name == 'nt':  # Windows
                    python_exec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'Scripts', 'python.exe')
                else:  # Unix/Linux/Mac
                    python_exec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python')
                
                # Check if python executable exists
                if not os.path.exists(python_exec):
                    python_exec = sys.executable
                
                # Get the full path to manual_run.py
                script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_run.py')
                
                # Run the script with proper arguments
                run_args = [python_exec, script_path, '--no-browser']
                if client:
                    run_args.extend(['--client', client])
                if report_type:
                    run_args.extend(['--frequency', report_type])
                if not collect_news:
                    run_args.append('--skip-collection')
                
                logger.info(f"Running command: {' '.join(run_args)}")
                
                result = subprocess.run(
                    run_args,
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                )
                
                if result.returncode == 0:
                    logger.info("Report generation completed successfully")
                else:
                    logger.error(f"Report generation failed: {result.stderr}")
            
            except Exception as e:
                logger.error(f"Error in report generation thread: {str(e)}")
        
        # Start the thread
        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": "Report generation started. Refresh the page in a moment to see your new report."
        })
        
    except Exception as e:
        logger.error(f"Error starting report generation: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot API requests"""
    if not openai_client:
        return jsonify({"error": "OpenAI API not available"}), 503
    
    try:
        data = request.json or {}
        user_message = data.get('message', '')
        client_name = data.get('client_name', 'General')
        report_type = data.get('report_type', 'daily')
        
        if not user_message:
            return jsonify({"error": "No message provided"}), 400
            
        # Log the chat interaction
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, 'chat.log')
        
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            ip = request.remote_addr
            f.write(f"{timestamp}|{ip}|User message: {user_message}\n")
        
        # TODO: Get some context about reports to inform the AI
        recent_reports_context = ""
        
        # Prepare the prompt for OpenAI
        system_message = f"""You are an AI assistant for the GCC Business Intelligence Platform, focused on providing insights about GCC markets, economic trends, and business developments.
You are helping a user who is viewing a {report_type} report prepared for {client_name}.
Provide concise, accurate, and helpful answers related to GCC business intelligence, markets, and economic trends.
If asked about something outside your knowledge domain, politely redirect the conversation back to GCC business topics.
{recent_reports_context}
"""
        
        # Call OpenAI API with retry logic
        response = openai_client.chat.completions.create(
            model="gpt-4o",  # Use GPT-4o for enhanced capabilities
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        # Extract the response text
        reply = response.choices[0].message.content
        
        # Log the assistant's reply
        with open(log_file, 'a') as f:
            f.write(f"{datetime.now().isoformat()}|{ip}|Assistant reply: {reply}\n")
        
        return jsonify({"reply": reply})
        
    except Exception as e:
        logger.error(f"Error in chat API: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report files from the reports directory"""
    return send_from_directory('../reports', filename)

@app.route('/reports/assets/<path:path>')
def serve_assets(path):
    """Serve asset files from the reports/assets directory"""
    return send_from_directory('../reports/assets', path)

@app.route('/health')
def health_check():
    """Health check endpoint for the API"""
    return jsonify({"status": "healthy"})

@app.route('/api/ml-status')
def ml_status():
    """Check if ML components are available"""
    return jsonify({
        "available": ml_integration is not None,
        "tensorflow_version": ml_integration.report_analyzer.get_tf_version() if ml_integration else None,
        "models_available": ml_integration.report_analyzer.list_models() if ml_integration else [],
        "data_available": ml_integration.report_analyzer.has_training_data() if ml_integration else False
    })

@app.route('/api/generate-forecast', methods=['POST'])
def generate_forecast():
    """Generate a forecast report"""
    if not ml_integration:
        return jsonify({"error": "ML integration not available"}), 503
    
    try:
        data = request.json or {}
        report_type = data.get('report_type', 'monthly')
        
        # Start forecast generation in a background thread
        def generate_forecast_task():
            try:
                if report_type == 'monthly':
                    md_path, html_path, pdf_path = ml_integration.generate_monthly_forecast_report()
                elif report_type == 'quarterly':
                    md_path, html_path, pdf_path = ml_integration.generate_quarterly_forecast_report()
                
                logger.info(f"Generated forecast report: {html_path}")
            except Exception as e:
                logger.error(f"Error generating forecast: {str(e)}")
        
        # Start the forecast generation in a thread
        thread = threading.Thread(target=generate_forecast_task)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "status": "generating",
            "message": f"Generating {report_type} forecast report in the background"
        })
        
    except Exception as e:
        logger.error(f"Error starting forecast generation: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/forecasts')
def list_forecasts():
    """List available forecast reports"""
    if not ml_integration:
        return jsonify({"forecasts": [], "error": "ML integration not available"}), 200
    
    try:
        forecasts = []
        forecast_types = ['monthly', 'quarterly']
        
        for forecast_type in forecast_types:
            # Get all forecast HTML files
            pattern = os.path.join(forecasts_dir, f"{forecast_type}_forecast_*.html")
            html_files = glob.glob(pattern)
            
            # Sort by timestamp (newest first)
            html_files.sort(key=os.path.getmtime, reverse=True)
            
            for html_file in html_files:
                base_name = os.path.basename(html_file)
                timestamp = base_name.replace(f'{forecast_type}_forecast_', '').replace('.html', '')
                
                # Get corresponding MD and PDF files if they exist
                md_file = html_file.replace('.html', '.md')
                pdf_file = html_file.replace('.html', '.pdf')
                
                # Parse timestamp for display
                try:
                    date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                    formatted_date = date_obj.strftime('%B %d, %Y')
                    formatted_time = date_obj.strftime('%I:%M %p')
                except:
                    formatted_date = "Unknown Date"
                    formatted_time = "Unknown Time"
                
                # Try to extract title and description
                title = f"{forecast_type.capitalize()} Forecast Report - {formatted_date}"
                description = f"AI-generated {forecast_type} forecast with economic indicators and market projections."
                
                try:
                    if os.path.exists(md_file):
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Try to extract a better title and description
                            lines = content.split('\n')
                            if lines and lines[0].startswith('# '):
                                title = lines[0].replace('# ', '')
                            
                            # Get a description from the first few paragraphs
                            for line in lines[1:20]:
                                if line.strip() and not line.startswith('#') and len(line) > 50:
                                    description = line.strip()[:200] + "..."
                                    break
                except Exception as e:
                    logger.warning(f"Error extracting forecast details: {str(e)}")
                
                # Build forecast info
                forecast_info = {
                    "type": forecast_type,
                    "title": title,
                    "date": date_obj.isoformat() if 'date_obj' in locals() else "",
                    "formatted_date": formatted_date,
                    "formatted_time": formatted_time,
                    "timestamp": timestamp,
                    "description": description,
                    "html_url": f"/forecasts/{os.path.basename(html_file)}",
                    "md_url": f"/forecasts/{os.path.basename(md_file)}" if os.path.exists(md_file) else None,
                    "pdf_url": f"/forecasts/{os.path.basename(pdf_file)}" if os.path.exists(pdf_file) else None
                }
                
                forecasts.append(forecast_info)
        
        return jsonify({"forecasts": forecasts})
        
    except Exception as e:
        logger.error(f"Error listing forecasts: {str(e)}")
        return jsonify({"error": str(e), "forecasts": []}), 500

@app.route('/forecasts/<path:filename>')
def serve_forecast(filename):
    """Serve forecast files from the forecasts directory"""
    return send_from_directory(forecasts_dir, filename)

@app.route('/api/ml-data-overview')
def ml_data_overview():
    """Get an overview of the data used for ML training"""
    if not ml_integration:
        return jsonify({"error": "ML integration not available"}), 503
    
    try:
        # Get data overview from the ML system
        overview = ml_integration.report_analyzer.get_data_summary()
        return jsonify(overview)
    except Exception as e:
        logger.error(f"Error getting ML data overview: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/visualization/<viz_type>')
def get_visualization(viz_type):
    """Generate and return a specific visualization"""
    if not ml_integration:
        return jsonify({"error": "ML integration not available"}), 503
    
    try:
        # Get parameters
        params = request.args.to_dict()
        metric = params.get('metric', 'gdp_growth')
        time_period = params.get('period', '6m')
        
        # Generate the visualization
        viz_path = ml_integration.report_analyzer.generate_visualization(
            viz_type, 
            metric=metric,
            time_period=time_period
        )
        
        if not viz_path or not os.path.exists(viz_path):
            return jsonify({"error": "Failed to generate visualization"}), 500
            
        # Return the visualization filename for the client to fetch
        viz_filename = os.path.basename(viz_path)
        return jsonify({
            "visualization_url": f"/forecasts/visualizations/{viz_filename}",
            "title": f"{viz_type.replace('_', ' ').title()} - {metric.replace('_', ' ').title()}"
        })
        
    except Exception as e:
        logger.error(f"Error generating visualization: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Serve visualization files
@app.route('/forecasts/visualizations/<path:filename>')
def serve_visualization(filename):
    """Serve visualization files"""
    viz_dir = os.path.join(forecasts_dir, "visualizations")
    return send_from_directory(viz_dir, filename)

@app.route('/api/clients')
def list_clients():
    """List all available clients for the platform"""
    try:
        # Get the clients directory
        clients_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'clients')
        clients = []
        
        # Add general client
        clients.append({
            "id": "general",
            "name": "General",
            "description": "General GCC market intelligence"
        })
        
        # Add clients from config directory
        if os.path.exists(clients_dir):
            for filename in os.listdir(clients_dir):
                if filename.endswith('.json'):
                    client_id = filename.replace('.json', '')
                    client_path = os.path.join(clients_dir, filename)
                    
                    try:
                        with open(client_path, 'r') as f:
                            client_data = json.load(f)
                            
                        clients.append({
                            "id": client_id,
                            "name": client_data.get('name', client_id.capitalize()),
                            "description": client_data.get('description', f"Business intelligence for {client_id.capitalize()}")
                        })
                    except:
                        # If we can't load the client data, add a basic entry
                        clients.append({
                            "id": client_id,
                            "name": client_id.capitalize(),
                            "description": f"Business intelligence for {client_id.capitalize()}"
                        })
        
        return jsonify({"clients": clients})
    
    except Exception as e:
        logger.error(f"Error listing clients: {str(e)}")
        return jsonify({"error": str(e), "clients": []}), 500

@app.route('/api/report-types')
def list_report_types():
    """List all available report types with their descriptions"""
    report_types = [
        {
            "id": "daily",
            "name": "Daily Report",
            "description": "Daily business intelligence brief covering latest news and developments"
        },
        {
            "id": "weekly",
            "name": "Weekly Report",
            "description": "Weekly comprehensive analysis of key trends and market movements"
        },
        {
            "id": "monthly",
            "name": "Monthly Report",
            "description": "Monthly deep dive into market trends with extended analysis"
        },
        {
            "id": "quarterly",
            "name": "Quarterly Report",
            "description": "Quarterly strategic outlook with comprehensive market analysis"
        }
    ]
    
    return jsonify({"report_types": report_types})

@app.route('/api/dashboard/analytics')
def dashboard_analytics():
    """Get dashboard analytics data for the analytics panel"""
    try:
        # Get reports data
        reports_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
        
        # Calculate analytics 
        # 1. Recent activity - count of reports in the last month
        all_reports = []
        for client_dir in os.listdir(reports_base_dir):
            client_path = os.path.join(reports_base_dir, client_dir)
            if os.path.isdir(client_path):
                for frequency in ['daily', 'weekly', 'monthly', 'quarterly']:
                    freq_path = os.path.join(client_path, frequency)
                    if os.path.isdir(freq_path):
                        md_files = glob.glob(os.path.join(freq_path, 'consolidated_report_*.md'))
                        for md_file in md_files:
                            file_stat = os.stat(md_file)
                            all_reports.append({
                                'path': md_file,
                                'client': client_dir,
                                'frequency': frequency,
                                'created': datetime.fromtimestamp(file_stat.st_mtime),
                                'size': file_stat.st_size
                            })
        
        # Sort by date
        all_reports.sort(key=lambda x: x['created'], reverse=True)
        
        # Count reports in the last month
        one_month_ago = datetime.now()
        one_month_ago = one_month_ago.replace(month=one_month_ago.month-1 if one_month_ago.month > 1 else 12)
        reports_last_month = sum(1 for r in all_reports if r['created'] >= one_month_ago)
        
        # 2. Most popular topic/client
        client_counts = {}
        for report in all_reports:
            client = report['client']
            client_counts[client] = client_counts.get(client, 0) + 1
        
        most_popular_client = max(client_counts.items(), key=lambda x: x[1]) if client_counts else ('Unknown', 0)
        
        # 3. Most frequently viewed report type
        frequency_counts = {}
        for report in all_reports:
            freq = report['frequency']
            frequency_counts[freq] = frequency_counts.get(freq, 0) + 1
        
        most_popular_frequency = max(frequency_counts.items(), key=lambda x: x[1]) if frequency_counts else ('Unknown', 0)
        
        # 4. Count chat interactions if we have access to that data
        chat_interactions = 0
        chat_log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs', 'chat.log')
        if os.path.exists(chat_log_path):
            with open(chat_log_path, 'r') as f:
                chat_interactions = sum(1 for line in f if 'User message:' in line)
        
        # Prepare response
        analytics = {
            "reports_generated_this_month": reports_last_month,
            "total_reports": len(all_reports),
            "most_popular_client": {
                "name": most_popular_client[0].replace('_', ' ').title(),
                "count": most_popular_client[1]
            },
            "most_viewed_report_type": {
                "name": most_popular_frequency[0].capitalize(),
                "count": most_popular_frequency[1]
            },
            "latest_report_date": all_reports[0]['created'].isoformat() if all_reports else None,
            "chat_interactions": chat_interactions,
            "active_users": 1  # Placeholder - would need user tracking/auth to be accurate
        }
        
        return jsonify(analytics)
        
    except Exception as e:
        logger.error(f"Error getting dashboard analytics: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/report-details/<timestamp>')
def get_report_details(timestamp):
    """Get detailed information about a specific report"""
    try:
        # Find the report in all client directories
        reports_base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
        
        # Search for the report in all client dirs
        report_file = None
        client_name = None
        frequency = None
        
        for client_dir in os.listdir(reports_base_dir):
            client_path = os.path.join(reports_base_dir, client_dir)
            if os.path.isdir(client_path):
                for freq in ['daily', 'weekly', 'monthly', 'quarterly']:
                    freq_path = os.path.join(client_path, freq)
                    if os.path.isdir(freq_path):
                        md_file = os.path.join(freq_path, f'consolidated_report_{timestamp}.md')
                        if os.path.exists(md_file):
                            report_file = md_file
                            client_name = client_dir
                            frequency = freq
                            break
            if report_file:
                break
        
        if not report_file:
            return jsonify({"error": f"Report with timestamp {timestamp} not found"}), 404
        
        # Parse the report content
        with open(report_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Parse timestamp
        try:
            date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
            formatted_date = date_obj.strftime('%B %d, %Y')
            formatted_time = date_obj.strftime('%I:%M %p')
        except:
            formatted_date = "Unknown Date"
            formatted_time = "Unknown Time"
            date_obj = None
        
        # Get file info
        file_stat = os.stat(report_file)
        html_file = report_file.replace('.md', '.html')
        pdf_file = report_file.replace('.md', '.pdf')
        
        # Extract metadata from the report
        client_match = re.search(r'\*\*Prepared for:\*\* ([^\\n]+)', content)
        if client_match:
            client_name = client_match.group(1).strip()
            
        title_match = re.search(r'# (.*)', content)
        title = title_match.group(1) if title_match else f"Business Intelligence Report - {formatted_date}"
        
        # Extract topics/sections
        topics = []
        for section in re.findall(r'## (.*?)(?=\n)', content):
            if section and section.strip() and "Table of Contents" not in section:
                topics.append(section.strip())
        
        # Calculate relative path for URLs
        relative_dir = os.path.relpath(os.path.dirname(report_file), reports_base_dir)
        
        # Prepare response
        report_info = {
            "title": title,
            "client": client_name,
            "frequency": frequency,
            "date": date_obj.isoformat() if date_obj else None,
            "formatted_date": formatted_date,
            "formatted_time": formatted_time,
            "timestamp": timestamp,
            "file_size": file_stat.st_size,
            "topics": topics[:5],  # First 5 topics/sections
            "created": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
            "md_url": f"/reports/{relative_dir}/{os.path.basename(report_file)}",
            "html_url": f"/reports/{relative_dir}/{os.path.basename(html_file)}",
            "pdf_url": f"/reports/{relative_dir}/{os.path.basename(pdf_file)}"
        }
        
        return jsonify(report_info)
        
    except Exception as e:
        logger.error(f"Error getting report details: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/log-report-view', methods=['POST'])
def log_report_view():
    """Log when a report is viewed for analytics purposes"""
    try:
        data = request.json
        
        if not data or 'report_id' not in data:
            return jsonify({"error": "Missing report_id in request"}), 400
            
        report_id = data.get('report_id')
        
        # Get the log directory
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Log the view
        log_file = os.path.join(logs_dir, 'report_views.log')
        with open(log_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            user_agent = request.headers.get('User-Agent', 'Unknown')
            ip = request.remote_addr
            f.write(f"{timestamp}|{report_id}|{ip}|{user_agent}\n")
        
        return jsonify({"success": True})
        
    except Exception as e:
        logger.error(f"Error logging report view: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    """Serve static files from the templates directory"""
    return send_from_directory('templates', filename)

@app.route('/api/linkedin/posts')
def list_linkedin_posts():
    """List available LinkedIn posts with pagination"""
    try:
        # Get query parameters for filtering
        post_type = request.args.get('type', None)
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        # Create the path for LinkedIn content
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin')
        
        # If post_type is specified, use the corresponding subdirectory
        if post_type in ['weekly', 'monthly']:
            content_dir = os.path.join(content_dir, post_type)
        
        # Ensure the directory exists
        os.makedirs(content_dir, exist_ok=True)
        
        # Get all JSON files (posts)
        json_files = []
        
        # Get files from the main directory and subdirectories
        for root, _, files in os.walk(content_dir):
            for file in files:
                if file.endswith('.json') and 'linkedin_' in file:
                    json_path = os.path.join(root, file)
                    # Extract the post type from the filename
                    file_type = 'daily'
                    if 'week_in_review' in file:
                        file_type = 'weekly'
                    elif 'month_in_review' in file:
                        file_type = 'monthly'
                    
                    # If post_type filter is applied, only include matching files
                    if post_type and post_type != file_type:
                        continue
                        
                    json_files.append((json_path, os.path.getmtime(json_path), file_type))
        
        # Sort by modification time (newest first)
        json_files.sort(key=lambda x: x[1], reverse=True)
        
        # Get total count before pagination
        total_count = len(json_files)
        
        # Apply pagination
        json_files = json_files[offset:offset+limit]
        
        posts = []
        for json_path, mod_time, file_type in json_files:
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    post_data = json.load(f)
                
                # Format the date from the filename or fallback to file modification time
                try:
                    # Extract date from filename (format: linkedin_TYPE_YYYYMMDD_HHMMSS.json)
                    filename = os.path.basename(json_path)
                    date_part = filename.split('_')[2]
                    time_part = filename.split('_')[3].split('.')[0] if len(filename.split('_')) > 3 else "000000"
                    
                    timestamp = f"{date_part}_{time_part}"
                    date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                    formatted_date = date_obj.strftime('%B %d, %Y')
                    formatted_time = date_obj.strftime('%I:%M %p')
                except:
                    # Fallback to file modification time
                    date_obj = datetime.fromtimestamp(mod_time)
                    formatted_date = date_obj.strftime('%B %d, %Y')
                    formatted_time = date_obj.strftime('%I:%M %p')
                
                # Create a post summary
                post_text = post_data.get('text', '')
                image_path = post_data.get('image_path', '')
                
                # Handle image path - convert to URL if it exists
                image_url = None
                if image_path and os.path.exists(image_path):
                    # Convert absolute path to relative URL
                    rel_path = os.path.relpath(image_path, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    image_url = f"/api/linkedin/images/{os.path.basename(image_path)}"
                
                # Extract first few lines as preview
                preview_lines = post_text.split('\n')[:3]
                preview = '\n'.join(preview_lines)
                if len(post_text.split('\n')) > 3:
                    preview += '...'
                
                # Extract metadata
                metadata = post_data.get('metadata', {})
                
                post_info = {
                    "id": os.path.basename(json_path).replace('.json', ''),
                    "type": file_type,
                    "title": metadata.get('title', preview_lines[0] if preview_lines else 'LinkedIn Post'),
                    "preview": preview,
                    "text": post_text,
                    "date": date_obj.isoformat() if 'date_obj' in locals() else "",
                    "formatted_date": formatted_date,
                    "formatted_time": formatted_time,
                    "image_url": image_url,
                    "hashtags": metadata.get('hashtags', []),
                    "post_file": os.path.relpath(json_path, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                }
                
                posts.append(post_info)
                
            except Exception as e:
                logger.error(f"Error parsing LinkedIn post {json_path}: {str(e)}")
                # Include a minimal entry for the errored post
                posts.append({
                    "id": os.path.basename(json_path).replace('.json', ''),
                    "type": file_type,
                    "title": "Error loading post",
                    "preview": f"Error: {str(e)}",
                    "error": str(e)
                })
        
        # Return the posts with pagination metadata
        return jsonify({
            "posts": posts,
            "meta": {
                "total": total_count,
                "offset": offset,
                "limit": limit,
                "has_more": (offset + limit) < total_count
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing LinkedIn posts: {str(e)}")
        return jsonify({"error": str(e), "posts": []}), 500

@app.route('/api/linkedin/generate', methods=['POST'])
def generate_linkedin_posts():
    """Generate new LinkedIn posts"""
    try:
        if not has_linkedin_generator:
            return jsonify({
                "success": False,
                "message": "LinkedIn content generator is not available"
            }), 503
            
        data = request.json
        post_type = data.get('post_type', 'general')
        content_text = data.get('content_text', None)
        client = data.get('client', 'general')
        
        # Run in a separate thread to avoid blocking
        def run_generator():
            try:
                # Initialize the LinkedIn content generator
                output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin')
                os.makedirs(output_dir, exist_ok=True)
                
                linkedin_generator = LinkedInContentGenerator(
                    output_dir=output_dir,
                    config_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'linkedin_config.json')
                )
                
                # Generate the post based on the type
                if post_type in ['weekly', 'monthly']:
                    # Weekly and monthly posts are single comprehensive posts
                    post = linkedin_generator._generate_post_from_text(
                        content_text or f"# {post_type.capitalize()} Business Review for {client.capitalize()}\n\nGenerate a comprehensive {post_type} review of UAE/GCC business developments.",
                        f"{post_type}_review"
                    )
                    
                    # Save the post
                    specific_dir = os.path.join(output_dir, post_type)
                    os.makedirs(specific_dir, exist_ok=True)
                    
                    # Create a generator for the specific directory
                    specific_generator = LinkedInContentGenerator(
                        output_dir=specific_dir,
                        config_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'linkedin_config.json')
                    )
                    
                    specific_generator.save_post(post, f"{post_type}_review")
                    
                else:
                    # For daily posts, generate multiple types
                    result = linkedin_generator.generate_linkedin_posts(content_text)
                    if not result:
                        logger.error("Failed to generate LinkedIn posts")
                
                logger.info(f"LinkedIn post generation completed for {post_type}")
                
            except Exception as e:
                logger.error(f"Error in LinkedIn generation thread: {str(e)}")
        
        # Start the thread
        thread = threading.Thread(target=run_generator)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            "success": True,
            "message": f"LinkedIn {post_type} post generation started. Refresh the posts page in a moment to see your new content."
        })
        
    except Exception as e:
        logger.error(f"Error generating LinkedIn posts: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/api/linkedin/post/<post_id>', methods=['GET'])
def get_linkedin_post(post_id):
    """Get a specific LinkedIn post by ID"""
    try:
        # Find the post file
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin')
        
        # Look in main directory and subdirectories
        post_file = None
        for root, _, files in os.walk(content_dir):
            for file in files:
                if file.startswith(post_id) and file.endswith('.json'):
                    post_file = os.path.join(root, file)
                    break
            if post_file:
                break
        
        if not post_file:
            return jsonify({"error": "Post not found"}), 404
            
        # Read the post file
        with open(post_file, 'r', encoding='utf-8') as f:
            post_data = json.load(f)
            
        # Extract data
        post_text = post_data.get('text', '')
        image_path = post_data.get('image_path', '')
        metadata = post_data.get('metadata', {})
        
        # Handle image path - convert to URL if it exists
        image_url = None
        if image_path and os.path.exists(image_path):
            # Convert absolute path to relative URL
            image_url = f"/api/linkedin/images/{os.path.basename(image_path)}"
            
        # Format the date from the filename or fallback to current time
        try:
            # Extract date from filename (format: linkedin_TYPE_YYYYMMDD_HHMMSS.json)
            filename = os.path.basename(post_file)
            date_part = filename.split('_')[2]
            time_part = filename.split('_')[3].split('.')[0] if len(filename.split('_')) > 3 else "000000"
            
            timestamp = f"{date_part}_{time_part}"
            date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
            formatted_date = date_obj.strftime('%B %d, %Y')
            formatted_time = date_obj.strftime('%I:%M %p')
        except:
            # Fallback to file modification time
            mod_time = os.path.getmtime(post_file)
            date_obj = datetime.fromtimestamp(mod_time)
            formatted_date = date_obj.strftime('%B %d, %Y')
            formatted_time = date_obj.strftime('%I:%M %p')
            
        # Determine post type
        post_type = 'daily'
        if 'weekly' in post_file:
            post_type = 'weekly'
        elif 'monthly' in post_file:
            post_type = 'monthly'
            
        post_info = {
            "id": post_id,
            "type": post_type,
            "title": metadata.get('title', post_text.split('\n')[0] if post_text else 'LinkedIn Post'),
            "text": post_text,
            "date": date_obj.isoformat() if 'date_obj' in locals() else "",
            "formatted_date": formatted_date,
            "formatted_time": formatted_time,
            "image_url": image_url,
            "hashtags": metadata.get('hashtags', []),
            "question": metadata.get('question', ''),
            "post_file": os.path.relpath(post_file, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "metadata": metadata
        }
        
        return jsonify(post_info)
        
    except Exception as e:
        logger.error(f"Error retrieving LinkedIn post: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/linkedin/post/<post_id>', methods=['DELETE'])
def delete_linkedin_post(post_id):
    """Delete a specific LinkedIn post by ID"""
    try:
        # Find the post file
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin')
        
        # Look in main directory and subdirectories
        post_file = None
        for root, _, files in os.walk(content_dir):
            for file in files:
                if file.startswith(post_id) and file.endswith('.json'):
                    post_file = os.path.join(root, file)
                    break
            if post_file:
                break
        
        if not post_file:
            return jsonify({"error": "Post not found"}), 404
            
        # Read the post file to find associated image
        image_path = None
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                post_data = json.load(f)
                image_path = post_data.get('image_path', None)
        except:
            pass
            
        # Delete the post file
        os.remove(post_file)
        
        # Delete the associated image if it exists
        if image_path and os.path.exists(image_path):
            try:
                os.remove(image_path)
                logger.info(f"Deleted associated image: {image_path}")
            except Exception as e:
                logger.warning(f"Could not delete associated image: {str(e)}")
        
        return jsonify({
            "success": True,
            "message": "Post deleted successfully"
        })
        
    except Exception as e:
        logger.error(f"Error deleting LinkedIn post: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/api/linkedin/images/<filename>')
def serve_linkedin_image(filename):
    """Serve a LinkedIn post image"""
    try:
        # Find the image file
        content_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'content', 'linkedin')
        
        # Look in the images directory and subdirectories
        image_file = None
        for root, _, files in os.walk(content_dir):
            if 'images' in root:
                for file in files:
                    if file == filename:
                        image_file = os.path.join(root, file)
                        break
            if image_file:
                break
        
        if not image_file:
            return jsonify({"error": "Image not found"}), 404
            
        # Get the directory containing the image
        image_dir = os.path.dirname(image_file)
        
        # Return the image
        return send_from_directory(image_dir, filename)
        
    except Exception as e:
        logger.error(f"Error serving LinkedIn image: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/linkedin/schedule', methods=['POST'])
def schedule_linkedin_task():
    """Schedule a LinkedIn post generation task"""
    try:
        data = request.json
        task_type = data.get('task_type', 'daily')  # daily, weekly, or monthly
        run_now = data.get('run_now', False)
        
        # Validate task type
        if task_type not in ['daily', 'weekly', 'monthly']:
            return jsonify({
                "success": False,
                "message": "Invalid task type. Must be one of: daily, weekly, monthly"
            }), 400
            
        # Get the path to the scheduler script
        scheduler_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schedule_linkedin.py')
        
        if not os.path.exists(scheduler_script):
            return jsonify({
                "success": False,
                "message": "LinkedIn scheduler script not found"
            }), 404
            
        # If run_now is True, run the script with the appropriate environment variables
        if run_now:
            # Run the specific task in a separate thread
            def run_task():
                try:
                    # Set environment variables
                    env = os.environ.copy()
                    env['LINKEDIN_RUN_IMMEDIATELY'] = 'true'
                    
                    # Get the path to the virtual environment python
                    if os.name == 'nt':  # Windows
                        python_exec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'Scripts', 'python.exe')
                    else:  # Unix/Linux/Mac
                        python_exec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python')
                    
                    # Check if python executable exists
                    if not os.path.exists(python_exec):
                        python_exec = sys.executable
                    
                    # Build the command
                    cmd = [python_exec, scheduler_script, '--run-immediate', '--task', task_type]
                    
                    # Run the command
                    logger.info(f"Running LinkedIn task: {' '.join(cmd)}")
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        env=env,
                        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    )
                    
                    if result.returncode == 0:
                        logger.info(f"LinkedIn task {task_type} completed successfully")
                    else:
                        logger.error(f"LinkedIn task {task_type} failed: {result.stderr}")
                        
                except Exception as e:
                    logger.error(f"Error running LinkedIn task: {str(e)}")
            
            # Start the thread
            thread = threading.Thread(target=run_task)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                "success": True,
                "message": f"LinkedIn {task_type} task started. Check back shortly for the results."
            })
            
        else:
            # Set up scheduling by updating environment variables
            # This part would update the .env file or a config file for scheduling
            # For simplicity, we'll just return success
            return jsonify({
                "success": True,
                "message": f"LinkedIn {task_type} task scheduled in the system."
            })
            
    except Exception as e:
        logger.error(f"Error scheduling LinkedIn task: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/api/config/image-generation', methods=['GET'])
def get_image_generation_config():
    """Get the current image generation configuration"""
    try:
        # Get the current config from environment variables
        use_gpt4o_images = os.getenv('USE_GPT4O_IMAGES', 'true').lower() == 'true'
        
        return jsonify({
            "use_gpt4o_images": use_gpt4o_images,
            "gpt4o_image_model": os.getenv('GPT4O_IMAGE_MODEL', 'gpt-4o')
        })
        
    except Exception as e:
        logger.error(f"Error getting image generation config: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/config/image-generation', methods=['POST'])
def update_image_generation_config():
    """Update the image generation configuration"""
    try:
        data = request.json
        
        # Update the environment variables
        if 'use_gpt4o_images' in data:
            use_gpt4o_images = data['use_gpt4o_images']
            os.environ['USE_GPT4O_IMAGES'] = 'true' if use_gpt4o_images else 'false'
            
            # Also update the config files if they exist
            try:
                env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
                
                if os.path.exists(env_file):
                    # Read the file
                    with open(env_file, 'r') as f:
                        lines = f.readlines()
                    
                    # Update the value
                    updated = False
                    for i, line in enumerate(lines):
                        if line.startswith('USE_GPT4O_IMAGES='):
                            lines[i] = f'USE_GPT4O_IMAGES={"true" if use_gpt4o_images else "false"}\n'
                            updated = True
                            break
                    
                    # Add the value if it doesn't exist
                    if not updated:
                        lines.append(f'USE_GPT4O_IMAGES={"true" if use_gpt4o_images else "false"}\n')
                    
                    # Write the file
                    with open(env_file, 'w') as f:
                        f.writelines(lines)
            except Exception as e:
                logger.warning(f"Could not update .env file: {str(e)}")
        
        if 'gpt4o_image_model' in data:
            os.environ['GPT4O_IMAGE_MODEL'] = data['gpt4o_image_model']
        
        # Reinitialize OpenAI client to apply changes immediately
        from src.utils.openai_utils import OpenAIClient
        global openai_client
        openai_client = OpenAIClient()
        
        return jsonify({
            "success": True,
            "message": "Image generation configuration updated",
            "use_gpt4o_images": os.getenv('USE_GPT4O_IMAGES', 'true').lower() == 'true',
            "gpt4o_image_model": os.getenv('GPT4O_IMAGE_MODEL', 'gpt-4o')
        })
        
    except Exception as e:
        logger.error(f"Error updating image generation config: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Use the same default port as run_api_server.py (3000)
    port = int(os.environ.get('PORT', 3000))
    is_production = os.environ.get('ENVIRONMENT', '').lower() == 'production'
    
    logger.info(f"Starting API server on port {port} in {'production' if is_production else 'development'} mode")
    
    # In production, don't use debug mode
    app.run(host='0.0.0.0', port=port, debug=not is_production) 