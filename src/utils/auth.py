#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Authentication and Authorization Module for GCC Business Intelligence Platform

Provides:
- User authentication with JWT tokens
- Role-based access control (RBAC)
- Session management
- Login rate limiting
"""

import os
import time
import json
import logging
import secrets
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum, auto

import jwt
from flask import request, jsonify, current_app, g, Response

# Try to import Redis cache, use in-memory fallback if not available
try:
    from src.utils.redis_cache import get_cache
    REDIS_CACHE_AVAILABLE = True
except ImportError:
    REDIS_CACHE_AVAILABLE = False
    
# Configure logging
logger = logging.getLogger(__name__)

# User roles
class Role(Enum):
    ADMIN = auto()
    ANALYST = auto()
    VIEWER = auto()
    CLIENT = auto()

    def __str__(self):
        return self.name
    
# Role permissions
ROLE_PERMISSIONS = {
    Role.ADMIN: {
        'manage_users': True,
        'manage_roles': True,
        'generate_report': True,
        'list_reports': True,
        'view_report': True,
        'delete_report': True,
        'system_settings': True,
        'view_analytics': True,
        'manage_collectors': True,
        'access_api': True,
        'manage_clients': True,
    },
    Role.ANALYST: {
        'generate_report': True,
        'list_reports': True,
        'view_report': True,
        'view_analytics': True,
        'manage_collectors': True,
        'access_api': True,
    },
    Role.VIEWER: {
        'list_reports': True,
        'view_report': True,
        'view_analytics': True,
    },
    Role.CLIENT: {
        'list_reports': True,
        'view_report': True,
    }
}

# In-memory user database (for demo/development purposes)
# In production, this would be replaced with a real database
DEFAULT_USERS = {
    "admin": {
        "password": "sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # 'password'
        "name": "Admin User",
        "role": Role.ADMIN,
        "client_id": None,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    },
    "analyst": {
        "password": "sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # 'password'
        "name": "Analyst User",
        "role": Role.ANALYST,
        "client_id": None,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    },
    "viewer": {
        "password": "sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # 'password'
        "name": "Viewer User",
        "role": Role.VIEWER,
        "client_id": None,
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    },
    "client": {
        "password": "sha256:5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8",  # 'password'
        "name": "Client User",
        "role": Role.CLIENT,
        "client_id": "general",
        "active": True,
        "created_at": datetime.utcnow().isoformat(),
    }
}

class AuthManager:
    """Authentication and Authorization Manager"""
    
    def __init__(self, 
                 secret_key: Optional[str] = None, 
                 token_expiry: int = 86400,  # 24 hours
                 refresh_token_expiry: int = 604800,  # 7 days
                 use_redis: bool = True,
                 max_login_attempts: int = 5,
                 block_duration: int = 300):  # 5 minutes
        """
        Initialize Auth Manager
        
        Args:
            secret_key: Secret key for JWT tokens
            token_expiry: JWT token expiry time in seconds
            refresh_token_expiry: Refresh token expiry time in seconds
            use_redis: Whether to use Redis for session storage
            max_login_attempts: Maximum number of failed login attempts
            block_duration: How long to block IP after max failed attempts (seconds)
        """
        # Get secret key from environment or use provided one
        self.secret_key = secret_key or os.environ.get('JWT_SECRET_KEY')
        if not self.secret_key:
            # Generate a random key if none provided (will invalidate existing tokens on restart)
            self.secret_key = secrets.token_hex(32)
            logger.warning("No JWT_SECRET_KEY provided. Generated random key (tokens will be invalidated on restart).")
            
        self.token_expiry = token_expiry
        self.refresh_token_expiry = refresh_token_expiry
        self.max_login_attempts = max_login_attempts
        self.block_duration = block_duration
        
        # Initialize Redis cache if available
        self.use_redis = use_redis and REDIS_CACHE_AVAILABLE
        if self.use_redis:
            self.cache = get_cache(cache_prefix="auth")
        else:
            self.cache = None
            self._sessions = {}  # In-memory sessions
            self._users = DEFAULT_USERS.copy()  # In-memory users
            self._failed_attempts = {}  # Track failed login attempts by IP
    
    def hash_password(self, password: str) -> str:
        """Hash a password using SHA-256"""
        return f"sha256:{hashlib.sha256(password.encode()).hexdigest()}"
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against stored hash"""
        if hashed.startswith("sha256:"):
            return hashed == self.hash_password(password)
        return False
    
    def _get_user(self, username: str) -> Optional[Dict]:
        """Get user data from storage"""
        if self.use_redis:
            user_data = self.cache.get(f"user:{username}")
            if user_data:
                # Convert role string back to Enum
                user_data['role'] = Role[user_data['role']] if isinstance(user_data['role'], str) else user_data['role']
                return user_data
        else:
            # Use in-memory storage
            return self._users.get(username)
        
        # If no user found, try to load from defaults
        if username in DEFAULT_USERS:
            return DEFAULT_USERS[username]
            
        return None
    
    def _save_user(self, username: str, user_data: Dict) -> bool:
        """Save user data to storage"""
        # Convert role to string for storage
        if 'role' in user_data and isinstance(user_data['role'], Role):
            user_data = user_data.copy()
            user_data['role'] = str(user_data['role'])
            
        if self.use_redis:
            return self.cache.set(f"user:{username}", user_data)
        else:
            # Use in-memory storage
            self._users[username] = user_data
            return True
    
    def _delete_user(self, username: str) -> bool:
        """Delete user from storage"""
        if self.use_redis:
            return self.cache.delete(f"user:{username}")
        else:
            # Use in-memory storage
            if username in self._users:
                del self._users[username]
                return True
            return False
    
    def _increment_failed_attempts(self, ip: str) -> int:
        """Increment failed login attempts for an IP"""
        if self.use_redis:
            # Increment counter in Redis
            count = self.cache.increment(f"failed_attempts:{ip}")
            # Set expiry if not already set
            self.cache.client.expire(f"failed_attempts:{ip}", self.block_duration)
            return count
        else:
            # Use in-memory counter
            now = time.time()
            if ip in self._failed_attempts:
                count, expiry = self._failed_attempts[ip]
                # Reset counter if expired
                if now > expiry:
                    count = 1
                    expiry = now + self.block_duration
                else:
                    count += 1
            else:
                count = 1
                expiry = now + self.block_duration
                
            self._failed_attempts[ip] = (count, expiry)
            return count
    
    def _check_failed_attempts(self, ip: str) -> bool:
        """Check if IP is blocked due to too many failed attempts"""
        if self.use_redis:
            count = self.cache.get(f"failed_attempts:{ip}")
            return count is not None and int(count) >= self.max_login_attempts
        else:
            if ip in self._failed_attempts:
                count, expiry = self._failed_attempts[ip]
                # Check if still within block duration
                if time.time() <= expiry:
                    return count >= self.max_login_attempts
            return False
    
    def _reset_failed_attempts(self, ip: str) -> None:
        """Reset failed login attempts for an IP after successful login"""
        if self.use_redis:
            self.cache.delete(f"failed_attempts:{ip}")
        else:
            if ip in self._failed_attempts:
                del self._failed_attempts[ip]
    
    def login(self, username: str, password: str, client_ip: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Authenticate a user and generate JWT token
        
        Args:
            username: Username
            password: Password
            client_ip: Client IP address for rate limiting
            
        Returns:
            Tuple of (success, user_data, error_message)
        """
        # Check if IP is blocked
        if self._check_failed_attempts(client_ip):
            wait_time = self.block_duration
            return False, None, f"Too many failed login attempts. Please try again in {wait_time} seconds."
        
        # Get user data
        user = self._get_user(username)
        if not user:
            # Increment failed attempts
            self._increment_failed_attempts(client_ip)
            return False, None, "Invalid username or password."
        
        # Check if user is active
        if not user.get('active', False):
            return False, None, "Account is inactive. Please contact an administrator."
        
        # Verify password
        if not self.verify_password(password, user['password']):
            # Increment failed attempts
            attempts = self._increment_failed_attempts(client_ip)
            remaining = self.max_login_attempts - attempts
            
            if remaining <= 0:
                return False, None, f"Too many failed login attempts. Please try again in {self.block_duration} seconds."
            else:
                return False, None, f"Invalid username or password. {remaining} attempts remaining."
        
        # Reset failed attempts on successful login
        self._reset_failed_attempts(client_ip)
        
        # Generate tokens
        user_data = {
            'username': username,
            'name': user.get('name', username),
            'role': str(user['role']) if isinstance(user['role'], Role) else user['role'],
            'client_id': user.get('client_id'),
        }
        
        access_token = self.generate_access_token(user_data)
        refresh_token = self.generate_refresh_token(username)
        
        # Store refresh token
        self._save_refresh_token(username, refresh_token)
        
        # Return success with tokens
        return True, {
            'user': user_data,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.token_expiry
        }, None
    
    def generate_access_token(self, user_data: Dict) -> str:
        """Generate a JWT access token"""
        payload = {
            'user': user_data,
            'exp': datetime.utcnow() + timedelta(seconds=self.token_expiry),
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def generate_refresh_token(self, username: str) -> str:
        """Generate a refresh token"""
        token = secrets.token_hex(32)
        return token
    
    def _save_refresh_token(self, username: str, token: str) -> bool:
        """Save refresh token to storage"""
        expires = int((datetime.utcnow() + timedelta(seconds=self.refresh_token_expiry)).timestamp())
        
        if self.use_redis:
            # Store token in Redis with expiry
            return self.cache.set(f"refresh_token:{token}", {
                'username': username,
                'expires': expires
            }, expire=self.refresh_token_expiry)
        else:
            # Store in-memory
            if not hasattr(self, '_refresh_tokens'):
                self._refresh_tokens = {}
            
            self._refresh_tokens[token] = {
                'username': username,
                'expires': expires
            }
            return True
    
    def _validate_refresh_token(self, token: str) -> Optional[str]:
        """
        Validate a refresh token and return username if valid
        
        Returns:
            Username if valid, None otherwise
        """
        if self.use_redis:
            token_data = self.cache.get(f"refresh_token:{token}")
        else:
            token_data = getattr(self, '_refresh_tokens', {}).get(token)
            
        if not token_data:
            return None
        
        # Check if token is expired
        expires = token_data.get('expires', 0)
        if int(time.time()) > expires:
            # Delete expired token
            if self.use_redis:
                self.cache.delete(f"refresh_token:{token}")
            else:
                if hasattr(self, '_refresh_tokens') and token in self._refresh_tokens:
                    del self._refresh_tokens[token]
            return None
        
        return token_data.get('username')
    
    def refresh_auth_token(self, refresh_token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Refresh an authentication token using a refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Tuple of (success, token_data, error_message)
        """
        # Validate refresh token
        username = self._validate_refresh_token(refresh_token)
        if not username:
            return False, None, "Invalid or expired refresh token."
        
        # Get user data
        user = self._get_user(username)
        if not user or not user.get('active', False):
            return False, None, "User account is inactive or deleted."
        
        # Generate new tokens
        user_data = {
            'username': username,
            'name': user.get('name', username),
            'role': str(user['role']) if isinstance(user['role'], Role) else user['role'],
            'client_id': user.get('client_id'),
        }
        
        access_token = self.generate_access_token(user_data)
        new_refresh_token = self.generate_refresh_token(username)
        
        # Store new refresh token and invalidate old one
        self._save_refresh_token(username, new_refresh_token)
        if self.use_redis:
            self.cache.delete(f"refresh_token:{refresh_token}")
        else:
            if hasattr(self, '_refresh_tokens') and refresh_token in self._refresh_tokens:
                del self._refresh_tokens[refresh_token]
        
        # Return success with tokens
        return True, {
            'user': user_data,
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'token_type': 'Bearer',
            'expires_in': self.token_expiry
        }, None
    
    def logout(self, refresh_token: str) -> bool:
        """
        Logout a user by invalidating their refresh token
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            bool: Success status
        """
        if self.use_redis:
            return self.cache.delete(f"refresh_token:{refresh_token}")
        else:
            if hasattr(self, '_refresh_tokens') and refresh_token in self._refresh_tokens:
                del self._refresh_tokens[refresh_token]
                return True
            return False
    
    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate a JWT token
        
        Args:
            token: JWT token
            
        Returns:
            Tuple of (is_valid, payload, error_message)
        """
        try:
            # Decode and validate token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check token type
            if payload.get('type') != 'access':
                return False, None, "Invalid token type."
            
            # Check if expired (jwt.decode should already handle this)
            return True, payload, None
            
        except jwt.ExpiredSignatureError:
            return False, None, "Token has expired."
        except jwt.InvalidTokenError as e:
            return False, None, f"Invalid token: {str(e)}"
        except Exception as e:
            logger.error(f"Error validating token: {e}")
            return False, None, "Error validating token."
    
    def check_permission(self, user_role: Union[str, Role], permission: str) -> bool:
        """
        Check if a role has a specific permission
        
        Args:
            user_role: User role (string or Enum)
            permission: Permission to check
            
        Returns:
            bool: True if the role has the permission
        """
        # Convert string role to Enum
        if isinstance(user_role, str):
            try:
                role = Role[user_role]
            except KeyError:
                logger.warning(f"Unknown role: {user_role}")
                return False
        else:
            role = user_role
        
        # Check if role exists in permissions dict
        if role not in ROLE_PERMISSIONS:
            return False
        
        # Check if permission exists for role
        return ROLE_PERMISSIONS[role].get(permission, False)
    
    def create_user(self, username: str, password: str, name: str, role: Union[str, Role], 
                   client_id: Optional[str] = None, active: bool = True) -> Tuple[bool, Optional[str]]:
        """
        Create a new user
        
        Args:
            username: Username
            password: Password
            name: Full name
            role: User role
            client_id: Optional client ID (for client users)
            active: Whether the account is active
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check if username already exists
        if self._get_user(username):
            return False, "Username already exists."
        
        # Convert string role to Enum
        if isinstance(role, str):
            try:
                role_enum = Role[role]
            except KeyError:
                return False, f"Invalid role: {role}"
        else:
            role_enum = role
        
        # Create user data
        user_data = {
            "password": self.hash_password(password),
            "name": name,
            "role": role_enum,
            "client_id": client_id,
            "active": active,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        # Save user
        success = self._save_user(username, user_data)
        if success:
            return True, None
        else:
            return False, "Error saving user data."
    
    def update_user(self, username: str, user_data: Dict) -> Tuple[bool, Optional[str]]:
        """
        Update an existing user
        
        Args:
            username: Username
            user_data: User data to update
            
        Returns:
            Tuple of (success, error_message)
        """
        # Get existing user
        existing_user = self._get_user(username)
        if not existing_user:
            return False, "User not found."
        
        # Update fields
        for field, value in user_data.items():
            if field == 'password':
                # Hash password if provided
                existing_user[field] = self.hash_password(value)
            elif field == 'role' and isinstance(value, str):
                # Convert string role to Enum
                try:
                    existing_user[field] = Role[value]
                except KeyError:
                    return False, f"Invalid role: {value}"
            else:
                existing_user[field] = value
        
        # Save updated user
        success = self._save_user(username, existing_user)
        if success:
            return True, None
        else:
            return False, "Error saving user data."
    
    def delete_user(self, username: str) -> Tuple[bool, Optional[str]]:
        """
        Delete a user
        
        Args:
            username: Username
            
        Returns:
            Tuple of (success, error_message)
        """
        # Check if user exists
        if not self._get_user(username):
            return False, "User not found."
        
        # Delete user
        success = self._delete_user(username)
        if success:
            return True, None
        else:
            return False, "Error deleting user."
    
    def list_users(self) -> List[Dict]:
        """
        List all users
        
        Returns:
            List of user data dictionaries
        """
        if self.use_redis:
            # List users from Redis (pattern match)
            user_keys = self.cache.client.keys("auth:user:*")
            users = []
            
            for key in user_keys:
                username = key.decode('utf-8').split(':')[-1] if isinstance(key, bytes) else key.split(':')[-1]
                user_data = self._get_user(username)
                if user_data:
                    # Exclude password
                    user_data = user_data.copy()
                    user_data.pop('password', None)
                    user_data['username'] = username
                    users.append(user_data)
            
            return users
        else:
            # List from in-memory users
            return [
                {**user_data.copy(), 'username': username, 'password': '********'}
                for username, user_data in self._users.items()
            ]

# Helper functions for Flask integration

# Singleton auth manager
_auth_manager = None

def get_auth_manager() -> AuthManager:
    """Get the global auth manager instance"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager(
            secret_key=os.environ.get('JWT_SECRET_KEY'),
            token_expiry=int(os.environ.get('JWT_TOKEN_EXPIRY', 86400)),
            refresh_token_expiry=int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRY', 604800)),
            use_redis=os.environ.get('USE_REDIS_AUTH', 'true').lower() == 'true',
            max_login_attempts=int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5)),
            block_duration=int(os.environ.get('BLOCK_DURATION', 300))
        )
    return _auth_manager

def token_required(f):
    """Decorator to require a valid JWT token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        # Get token from Authorization header
        if auth_header:
            parts = auth_header.split()
            if len(parts) == 2 and parts[0].lower() == 'bearer':
                token = parts[1]
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        auth_manager = get_auth_manager()
        valid, payload, error = auth_manager.validate_token(token)
        
        if not valid:
            return jsonify({'message': error or 'Invalid token'}), 401
        
        # Set current user in Flask global context
        g.current_user = payload['user']
        
        return f(*args, **kwargs)
    
    return decorated

def permission_required(permission):
    """
    Decorator to require a specific permission
    Must be used after @token_required
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Check if user is set in context by token_required
            if not hasattr(g, 'current_user'):
                return jsonify({'message': 'Authentication required'}), 401
            
            # Get user role
            user_role = g.current_user.get('role')
            if not user_role:
                return jsonify({'message': 'Invalid user role'}), 403
            
            # Check permission
            auth_manager = get_auth_manager()
            if not auth_manager.check_permission(user_role, permission):
                return jsonify({'message': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator

def client_filter(f):
    """
    Decorator to filter data based on client_id
    Must be used after @token_required
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Get client_id from current user
        if hasattr(g, 'current_user'):
            client_id = g.current_user.get('client_id')
            
            # For non-client roles, don't filter
            user_role = g.current_user.get('role')
            auth_manager = get_auth_manager()
            
            if isinstance(user_role, str):
                try:
                    role = Role[user_role]
                except KeyError:
                    role = None
            else:
                role = user_role
            
            # Only apply client filtering to CLIENT role
            if role == Role.CLIENT and client_id:
                # Make client_id available to the route function
                kwargs['client_id'] = client_id
        
        return f(*args, **kwargs)
    
    return decorated

# Basic setup for flask_login compatibility
def init_app(app):
    """
    Initialize Flask app with authentication
    
    Args:
        app: Flask app
    """
    # Initialize auth manager
    auth_manager = get_auth_manager()
    
    # Add login route
    @app.route('/api/login', methods=['POST'])
    def login():
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'message': 'Username and password are required'}), 400
        
        success, token_data, error = auth_manager.login(username, password, request.remote_addr)
        
        if success:
            return jsonify(token_data), 200
        else:
            return jsonify({'message': error or 'Login failed'}), 401
    
    # Add token refresh route
    @app.route('/api/refresh-token', methods=['POST'])
    def refresh_token():
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'message': 'Refresh token is required'}), 400
        
        success, token_data, error = auth_manager.refresh_auth_token(refresh_token)
        
        if success:
            return jsonify(token_data), 200
        else:
            return jsonify({'message': error or 'Token refresh failed'}), 401
    
    # Add logout route
    @app.route('/api/logout', methods=['POST'])
    def logout():
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return jsonify({'message': 'Refresh token is required'}), 400
        
        success = auth_manager.logout(refresh_token)
        
        if success:
            return jsonify({'message': 'Logout successful'}), 200
        else:
            return jsonify({'message': 'Logout failed'}), 400
    
    # Add user management routes (admin only)
    @app.route('/api/users', methods=['GET'])
    @token_required
    @permission_required('manage_users')
    def list_users():
        users = auth_manager.list_users()
        return jsonify({'users': users}), 200
    
    @app.route('/api/users', methods=['POST'])
    @token_required
    @permission_required('manage_users')
    def create_user():
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        username = data.get('username')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role')
        client_id = data.get('client_id')
        active = data.get('active', True)
        
        if not all([username, password, name, role]):
            return jsonify({'message': 'Username, password, name, and role are required'}), 400
        
        success, error = auth_manager.create_user(
            username=username,
            password=password,
            name=name,
            role=role,
            client_id=client_id,
            active=active
        )
        
        if success:
            return jsonify({'message': 'User created successfully'}), 201
        else:
            return jsonify({'message': error or 'User creation failed'}), 400
    
    @app.route('/api/users/<username>', methods=['PUT'])
    @token_required
    @permission_required('manage_users')
    def update_user(username):
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        success, error = auth_manager.update_user(username, data)
        
        if success:
            return jsonify({'message': 'User updated successfully'}), 200
        else:
            return jsonify({'message': error or 'User update failed'}), 400
    
    @app.route('/api/users/<username>', methods=['DELETE'])
    @token_required
    @permission_required('manage_users')
    def delete_user(username):
        success, error = auth_manager.delete_user(username)
        
        if success:
            return jsonify({'message': 'User deleted successfully'}), 200
        else:
            return jsonify({'message': error or 'User deletion failed'}), 400
    
    # Add middleware to check token on all /api routes
    @app.before_request
    def check_token_middleware():
        # Skip auth for login/refresh/logout routes
        path = request.path
        if path == '/api/login' or path == '/api/refresh-token' or path == '/api/logout':
            return None
        
        # Skip auth for non-API routes
        if not path.startswith('/api/'):
            return None
        
        # For API routes, check for token if we're enforcing auth
        if os.environ.get('ENFORCE_API_AUTH', 'false').lower() == 'true':
            token = None
            auth_header = request.headers.get('Authorization')
            
            # Get token from Authorization header
            if auth_header:
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    token = parts[1]
            
            if not token:
                return jsonify({'message': 'Authentication required'}), 401
            
            valid, payload, error = auth_manager.validate_token(token)
            
            if not valid:
                return jsonify({'message': error or 'Invalid token'}), 401
            
            # Set current user in Flask global context
            g.current_user = payload['user']
    
    # Add health check route
    @app.route('/api/auth/health', methods=['GET'])
    def auth_health():
        return jsonify({'status': 'ok'}), 200
    
    # Return auth manager instance
    return auth_manager 