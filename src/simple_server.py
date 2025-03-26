import os
import sys
import logging
from flask import Flask, render_template, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__, 
    static_folder='../reports',
    template_folder='templates'
)

@app.route('/')
def index():
    """Serve the landing page"""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for the API"""
    return jsonify({"status": "healthy", "message": "Global Possibilities Business Intelligence API"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8000))
    
    logger.info(f"Starting simple server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=True) 