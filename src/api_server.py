import os
import sys
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
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

app = Flask(__name__, static_folder='../reports')
CORS(app)  # Enable CORS for all routes

# Initialize OpenAI client
api_key = os.getenv('OPENAI_API_KEY')
openai_client = OpenAIClient(api_key) if api_key else None

@app.route('/')
def index():
    """Return a simple message for the root URL"""
    return jsonify({
        "message": "Global Possibilities Business Intelligence API",
        "status": "running"
    })

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