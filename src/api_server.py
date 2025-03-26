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
        
        return jsonify({"reports": reports})
    
    except Exception as e:
        logger.error(f"Error listing reports: {str(e)}")
        return jsonify({"error": str(e), "reports": []}), 500

@app.route('/api/generate-report', methods=['POST'])
def generate_report():
    """Generate a new report using the manual_run.py script"""
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
            "message": f"Report generation started for client: {client}, type: {report_type}. This will take a few minutes."
        })
    
    except Exception as e:
        logger.error(f"Error triggering report generation: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chatbot API requests"""
    data = request.json
    message = data.get('message', '')
    report_content = data.get('report_content', '')
    client_name = data.get('client_name', 'General')
    report_type = data.get('report_type', 'daily')
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    if not openai_client:
        return jsonify({"error": "OpenAI API key not configured"}), 500
    
    try:
        # Create system prompt with context about GCC business
        system_prompt = (
            f"You are a knowledgeable business intelligence assistant specializing in GCC region "
            f"economics and business trends. Your responses should be helpful, professional, and "
            f"focused on providing accurate information about UAE and GCC business topics. "
            f"Keep responses concise (2-3 paragraphs maximum) but informative.\n\n"
            f"This is a {report_type} report prepared for {client_name}."
        )
        
        # If report content is provided, add it to the context
        if report_content:
            system_prompt += (
                "\n\nYou have access to the following report content. Use this information "
                "to provide accurate and relevant answers to user questions:\n\n" + report_content
            )
        
        # Call OpenAI with the user message
        response = openai_client.create_chat_completion(
            model="gpt-4o",  # Use the more powerful model for better responses
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=600,
            temperature=0.7
        )
        
        # Extract the assistant's reply
        reply = response.choices[0].message.content.strip()
        logger.info(f"Generated chatbot response for {client_name} query: {message[:30]}...")
        
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
    """List all available clients with their descriptions"""
    try:
        clients = []
        clients_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config', 'clients')
        
        if not os.path.exists(clients_dir):
            return jsonify({"error": "Clients directory not found", "clients": []})
        
        for filename in os.listdir(clients_dir):
            if filename.endswith('.json'):
                client_id = filename.replace('.json', '')
                try:
                    with open(os.path.join(clients_dir, filename), 'r') as f:
                        config = json.load(f)
                        clients.append({
                            "id": client_id,
                            "name": config.get("name", client_id.capitalize()),
                            "description": config.get("description", "Client-specific reports"),
                            "include_linkedin": config.get("include_linkedin", False),
                            "include_chatbot": config.get("include_chatbot", True)
                        })
                except Exception as e:
                    logger.error(f"Error loading client config '{client_id}': {str(e)}")
                    clients.append({
                        "id": client_id,
                        "name": client_id.capitalize(),
                        "description": "Client-specific reports",
                        "include_linkedin": False,
                        "include_chatbot": True
                    })
        
        # Sort by name
        clients = sorted(clients, key=lambda x: x["id"])
        
        # Always include the general client if it doesn't exist
        if not any(c["id"] == "general" for c in clients):
            clients.insert(0, {
                "id": "general",
                "name": "Global Possibilities Team",
                "description": "Internal team report with full analysis",
                "include_linkedin": True,
                "include_chatbot": True
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('ENVIRONMENT', '').lower() == 'production'
    
    logger.info(f"Starting API server on port {port} in {'production' if is_production else 'development'} mode")
    
    # In production, don't use debug mode
    app.run(host='0.0.0.0', port=port, debug=not is_production) 