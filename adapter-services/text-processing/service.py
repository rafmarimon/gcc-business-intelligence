"""
Text Processing Service for GCC Business Intelligence.

This service provides endpoints for processing text data, including:
- Content enrichment
- Entity extraction
- Text summarization
- Topic classification

The service is designed to be called from Low-Code Airbyte connectors
to handle advanced NLP tasks that would normally require Python CDK.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional, Union

from flask import Flask, jsonify, request
import nltk
import openai
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = openai.OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Download NLTK resources
nltk.download("punkt")
nltk.download("stopwords")


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/enrich", methods=["POST"])
def enrich_content():
    """
    Enrich content with additional context and metadata.
    
    This endpoint adds:
    - Sentiment analysis
    - Key entities
    - Content classification
    - Related topics
    
    Used by Low-Code connectors to enhance the extracted content.
    """
    try:
        data = request.json
        if not data or not isinstance(data, dict):
            return jsonify({"error": "Invalid input data"}), 400
        
        # Extract text content from various possible fields
        content = ""
        if "content" in data:
            content = data["content"]
        elif "body" in data:
            content = data["body"]
        elif "text" in data:
            content = data["text"]
        elif "article" in data:
            content = data["article"]
        
        if not content or len(content) < 10:
            return jsonify({"error": "Insufficient content for enrichment"}), 400
        
        # Perform enrichment
        enriched_data = data.copy()
        
        # Add sentiment analysis using OpenAI
        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert in analyzing GCC business and economic texts."},
                    {"role": "user", "content": f"Analyze the following text and provide the sentiment (positive, neutral, negative), key entities, topics, and a brief summary in JSON format:\n\n{content[:4000]}"}
                ],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            
            # Add the analysis to enriched data
            enriched_data["analysis"] = analysis
            
        except Exception as e:
            logger.error(f"Error in OpenAI enrichment: {str(e)}")
            enriched_data["analysis"] = {
                "error": "Failed to perform AI analysis",
                "details": str(e)
            }
        
        # Add basic text statistics
        words = nltk.word_tokenize(content)
        sentences = nltk.sent_tokenize(content)
        enriched_data["text_stats"] = {
            "word_count": len(words),
            "sentence_count": len(sentences),
            "avg_sentence_length": len(words) / max(len(sentences), 1)
        }
        
        return jsonify(enriched_data), 200
        
    except Exception as e:
        logger.error(f"Error in content enrichment: {str(e)}")
        return jsonify({"error": f"Failed to process content: {str(e)}"}), 500


@app.route("/transform", methods=["POST"])
def transform_data():
    """
    Transform incoming data from a connector.
    
    This endpoint:
    - Standardizes field names
    - Cleans up text content
    - Processes raw content for better downstream consumption
    
    Used by Low-Code connectors to normalize data.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        # Transform the data
        transformed_data = data.copy()
        
        # Standardize field names if necessary
        field_mapping = {
            "Article": "article",
            "Title": "title",
            "Headline": "title",
            "Body": "content",
            "Content": "content",
            "PublishedAt": "published_at",
            "PublishedDate": "published_at",
            "Author": "author",
            "Source": "source"
        }
        
        for old_key, new_key in field_mapping.items():
            if old_key in transformed_data and old_key != new_key:
                transformed_data[new_key] = transformed_data.pop(old_key)
        
        # Clean text content if present
        if "content" in transformed_data and isinstance(transformed_data["content"], str):
            # Basic cleaning
            content = transformed_data["content"]
            content = content.replace("\r", " ").replace("\n\n", "\n").strip()
            transformed_data["content"] = content
            
            # Add a cleaned version without HTML if needed
            if "<" in content and ">" in content:
                import re
                clean_content = re.sub(r'<[^>]+>', '', content)
                transformed_data["content_clean"] = clean_content
        
        # Add processing timestamp
        from datetime import datetime
        transformed_data["processed_at"] = datetime.utcnow().isoformat()
        
        return jsonify(transformed_data), 200
        
    except Exception as e:
        logger.error(f"Error in data transformation: {str(e)}")
        return jsonify({"error": f"Failed to transform data: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8090))
    app.run(host="0.0.0.0", port=port) 