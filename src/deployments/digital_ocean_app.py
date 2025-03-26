import os
import sys
import logging
from flask import Flask, render_template, jsonify, send_from_directory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
    static_folder='../../reports',
    template_folder='../templates'
)

@app.route('/')
def index():
    """Serve the landing page"""
    try:
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering template: {str(e)}")
        return jsonify({"status": "error", "message": f"Error rendering template: {str(e)}"}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for the API"""
    return jsonify({
        "status": "healthy", 
        "message": "Global Possibilities Business Intelligence API", 
        "version": "1.0.0"
    })

@app.route('/reports/<path:filename>')
def serve_report(filename):
    """Serve report files from the reports directory"""
    try:
        return send_from_directory('../../reports', filename)
    except Exception as e:
        logger.error(f"Error serving report file {filename}: {str(e)}")
        return jsonify({"status": "error", "message": f"Error serving file: {str(e)}"}), 404

# For gunicorn
application = app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    
    logger.info(f"Starting Digital Ocean app on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=True) 