"""
Authentication Service for GCC Business Intelligence.

This service provides endpoints for authentication tasks, including:
- OAuth2 token management
- API key validation
- Custom credential handling

The service is designed to be called from Low-Code Airbyte connectors
to handle authentication that would normally require Python CDK.
"""

import os
import time
import json
import logging
from typing import Dict, Optional

import jwt
import redis
import requests
from flask import Flask, jsonify, request
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configure Redis for token caching (if available)
REDIS_URL = os.environ.get("REDIS_URL")
redis_client = None
if REDIS_URL:
    try:
        redis_client = redis.from_url(REDIS_URL)
        logger.info("Redis connection established for token caching")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {str(e)}")


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"}), 200


@app.route("/get-token", methods=["GET"])
def get_auth_token():
    """
    Get authentication token for the GCC News API.
    
    This endpoint:
    1. Checks for a cached token in Redis
    2. If not found or expired, generates a new one
    3. Caches the new token with expiration
    4. Returns the token for connectors to use
    
    Used by Low-Code connectors to authenticate with APIs.
    """
    try:
        # Get client credentials from environment
        client_id = os.environ.get("CLIENT_ID")
        client_secret = os.environ.get("CLIENT_SECRET")
        
        if not client_id or not client_secret:
            return jsonify({"error": "Missing required credentials"}), 401
        
        # Check for cached token
        token = None
        if redis_client:
            cached_token = redis_client.get("gcc_api_token")
            if cached_token:
                token_data = json.loads(cached_token)
                # Check if token is still valid (with 5-minute buffer)
                if token_data.get("expires_at", 0) > time.time() + 300:
                    logger.info("Using cached token")
                    return jsonify({"token": token_data["access_token"]}), 200
        
        # If no valid cached token, get a new one
        auth_url = "https://example.com/gcc/api/oauth/token"
        
        # Make token request
        response = requests.post(
            auth_url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "read write"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # For demo purposes (since this is just a mock)
        # In real implementation, this would actually call the OAuth endpoint
        # This is a simulation of the response
        current_time = time.time()
        token_data = {
            "access_token": f"gcc-api-token-{int(current_time)}",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": current_time + 3600,
            "scope": "read write"
        }
        
        # Cache the token
        if redis_client:
            redis_client.setex(
                "gcc_api_token",
                3600,  # TTL in seconds (1 hour)
                json.dumps(token_data)
            )
            logger.info("New token cached")
        
        return jsonify({"token": token_data["access_token"]}), 200
        
    except Exception as e:
        logger.error(f"Error generating auth token: {str(e)}")
        return jsonify({"error": f"Failed to generate token: {str(e)}"}), 500


@app.route("/validate-api-key", methods=["POST"])
def validate_api_key():
    """
    Validate an API key for custom API implementations.
    
    This endpoint:
    1. Validates the API key format
    2. Checks if the key is authorized
    3. Returns whether the key is valid and its permissions
    """
    try:
        data = request.json
        if not data or "api_key" not in data:
            return jsonify({"error": "API key is required"}), 400
            
        api_key = data["api_key"]
        
        # In a real implementation, validate against a secure database
        # This is a simulation for demonstration purposes
        if api_key.startswith("gcc-api-"):
            return jsonify({
                "valid": True,
                "permissions": ["read", "write"],
                "rate_limit": 100
            }), 200
        else:
            return jsonify({"valid": False}), 401
            
    except Exception as e:
        logger.error(f"Error validating API key: {str(e)}")
        return jsonify({"error": f"Validation failed: {str(e)}"}), 500


@app.route("/custom-auth", methods=["POST"])
def custom_auth_handler():
    """
    Handle custom authentication schemes not supported by Low-Code CDK.
    
    This endpoint adapts complex authentication methods into a format
    that Low-Code connectors can use.
    """
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No auth data provided"}), 400
            
        # Handle various authentication schemes
        auth_type = data.get("auth_type", "")
        
        if auth_type == "hmac":
            # Example of HMAC authentication
            secret = os.environ.get("HMAC_SECRET", "")
            message = data.get("message", "")
            timestamp = str(int(time.time()))
            
            import hashlib
            import hmac as hmac_lib
            
            h = hmac_lib.new(
                secret.encode(),
                f"{message}{timestamp}".encode(),
                hashlib.sha256
            )
            signature = h.hexdigest()
            
            return jsonify({
                "signature": signature,
                "timestamp": timestamp,
                "headers": {
                    "X-GCC-Signature": signature,
                    "X-GCC-Timestamp": timestamp
                }
            }), 200
            
        elif auth_type == "jwt":
            # Example of JWT token generation
            secret = os.environ.get("JWT_SECRET", "")
            payload = data.get("payload", {})
            
            # Add standard claims
            if "exp" not in payload:
                payload["exp"] = int(time.time()) + 3600  # 1 hour
            if "iat" not in payload:
                payload["iat"] = int(time.time())
                
            token = jwt.encode(payload, secret, algorithm="HS256")
            
            return jsonify({
                "token": token,
                "expires_at": payload["exp"],
                "headers": {
                    "Authorization": f"Bearer {token}"
                }
            }), 200
            
        else:
            return jsonify({"error": f"Unsupported auth type: {auth_type}"}), 400
            
    except Exception as e:
        logger.error(f"Error in custom auth: {str(e)}")
        return jsonify({"error": f"Authentication failed: {str(e)}"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8091))
    app.run(host="0.0.0.0", port=port) 