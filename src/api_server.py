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

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import our custom OpenAI client with exponential backoff
from src.utils.openai_utils import OpenAIClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__, 
    static_folder='../reports',
    template_folder='templates'
)
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAIClient(api_key) if api_key else None

@app.route('/')
def index():
    """Serve the landing page"""
    return render_template('index.html')

@app.route('/api/reports')
def list_reports():
    """List the available reports"""
    try:
        reports_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
        reports = []
        
        # Get all consolidated report markdown files
        md_files = glob.glob(os.path.join(reports_dir, 'consolidated_report_*.md'))
        
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
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Skip title and get the actual content
                    parts = content.split('---', 2)
                    if len(parts) > 2:
                        actual_content = parts[2]
                    else:
                        actual_content = content
                    
                    # Extract a brief description
                    description = actual_content.strip()[:200] + "..."
            except:
                description = "Daily business intelligence report on GCC and UAE markets."
            
            report_info = {
                "title": f"Business Intelligence Report - {formatted_date}",
                "date": date_obj.isoformat() if 'date_obj' in locals() else "",
                "formatted_date": formatted_date,
                "formatted_time": formatted_time,
                "timestamp": timestamp,
                "description": description,
                "md_url": f"/reports/{os.path.basename(md_file)}",
                "html_url": f"/reports/{os.path.basename(html_file)}",
                "pdf_url": f"/reports/{os.path.basename(pdf_file)}"
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
        
        # Prepare command arguments
        cmd_args = ['python', 'src/manual_run.py', '--no-browser']
        
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
            "message": "Report generation started. This will take a few minutes."
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
    
    if not message:
        return jsonify({"error": "No message provided"}), 400
    
    if not openai_client:
        return jsonify({"error": "OpenAI API key not configured"}), 500
    
    try:
        # Create system prompt with context about GCC business
        system_prompt = (
            "You are a knowledgeable business intelligence assistant specializing in GCC region "
            "economics and business trends. Your responses should be helpful, professional, and "
            "focused on providing accurate information about UAE and GCC business topics. "
            "Keep responses concise (2-3 paragraphs maximum) but informative."
        )
        
        # If report content is provided, add it to the context
        if report_content:
            system_prompt += (
                "\n\nYou have access to the following report content. Use this information "
                "to provide accurate and relevant answers to user questions:\n\n" + report_content
            )
        
        # Call OpenAI with the user message
        response = openai_client.create_chat_completion(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        # Extract the assistant's reply
        reply = response.choices[0].message.content.strip()
        logger.info(f"Generated chatbot response for query: {message[:30]}...")
        
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    is_production = os.environ.get('ENVIRONMENT', '').lower() == 'production'
    
    logger.info(f"Starting API server on port {port} in {'production' if is_production else 'development'} mode")
    
    # In production, don't use debug mode
    app.run(host='0.0.0.0', port=port, debug=not is_production) 