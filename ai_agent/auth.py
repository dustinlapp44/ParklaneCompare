"""
Authentication and Authorization System for AI Agent
Implements JWT-based authentication with role-based access control
"""

import jwt
import bcrypt
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Optional, Dict, Any
from flask import request, jsonify, session, current_app
from production_config import get_config

logger = logging.getLogger(__name__)

class AuthManager:
    """Handles authentication and authorization"""
    
    def __init__(self, config):
        self.config = config
        self.secret_key = config.JWT_SECRET_KEY
        self.token_expires = config.JWT_ACCESS_TOKEN_EXPIRES
        
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    def generate_token(self, user_data: Dict[str, Any]) -> str:
        """Generate a JWT token for a user"""
        payload = {
            'user_id': user_data.get('user_id'),
            'username': user_data.get('username'),
            'role': user_data.get('role', 'user'),
            'exp': datetime.utcnow() + self.token_expires,
            'iat': datetime.utcnow()
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user with username and password"""
        # For now, we have a simple admin user
        if username == self.config.ADMIN_USERNAME:
            if self.config.ADMIN_PASSWORD_HASH and self.verify_password(password, self.config.ADMIN_PASSWORD_HASH):
                return {
                    'user_id': 1,
                    'username': username,
                    'role': 'admin'
                }
        
        return None

# Global auth manager instance
auth_manager = None

def init_auth(config):
    """Initialize the authentication system"""
    global auth_manager
    auth_manager = AuthManager(config)
    return auth_manager

def require_auth(roles: Optional[list] = None):
    """Decorator to require authentication for API endpoints"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            config = get_config()
            
            # Skip auth if disabled in config
            if not config.AUTH_ENABLED:
                return f(*args, **kwargs)
            
            # Check for token in Authorization header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401
            
            token = auth_header.split(' ')[1]
            user_data = auth_manager.verify_token(token)
            
            if not user_data:
                return jsonify({'error': 'Invalid or expired token', 'code': 'INVALID_TOKEN'}), 401
            
            # Check role permissions if specified
            if roles and user_data.get('role') not in roles:
                return jsonify({'error': 'Insufficient permissions', 'code': 'INSUFFICIENT_PERMISSIONS'}), 403
            
            # Add user data to request context
            request.current_user = user_data
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def require_admin(f):
    """Decorator to require admin role"""
    return require_auth(['admin'])(f)

def get_current_user() -> Optional[Dict[str, Any]]:
    """Get the current authenticated user"""
    return getattr(request, 'current_user', None)

def audit_log(action: str, details: Dict[str, Any] = None):
    """Log user actions for audit trail"""
    user = get_current_user()
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'user_id': user.get('user_id') if user else None,
        'username': user.get('username') if user else 'anonymous',
        'action': action,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent'),
        'details': details or {}
    }
    
    # Log to file for audit trail
    logger.info(f"AUDIT: {log_entry}")
    
    return log_entry

def generate_admin_password_hash(password: str) -> str:
    """Utility function to generate password hash for admin user"""
    config = get_config()
    auth = AuthManager(config)
    return auth.hash_password(password)

# Authentication API endpoints
def create_auth_routes(app):
    """Create authentication routes"""
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """User login endpoint"""
        try:
            data = request.get_json()
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return jsonify({'error': 'Username and password required'}), 400
            
            user_data = auth_manager.authenticate_user(username, password)
            if user_data:
                token = auth_manager.generate_token(user_data)
                
                audit_log('user_login', {'username': username})
                
                return jsonify({
                    'token': token,
                    'user': {
                        'username': user_data['username'],
                        'role': user_data['role']
                    },
                    'expires_in': auth_manager.token_expires.total_seconds()
                })
            else:
                audit_log('login_failed', {'username': username})
                return jsonify({'error': 'Invalid credentials'}), 401
                
        except Exception as e:
            logger.error(f"Login error: {e}")
            return jsonify({'error': 'Login failed'}), 500
    
    @app.route('/api/auth/verify', methods=['GET'])
    @require_auth()
    def verify_token():
        """Verify token endpoint"""
        user = get_current_user()
        return jsonify({
            'valid': True,
            'user': {
                'username': user['username'],
                'role': user['role']
            }
        })
    
    @app.route('/api/auth/logout', methods=['POST'])
    @require_auth()
    def logout():
        """User logout endpoint"""
        user = get_current_user()
        audit_log('user_logout', {'username': user['username']})
        
        # Note: With JWT, we can't truly "logout" without a blacklist
        # For now, just log the action
        return jsonify({'message': 'Logged out successfully'})


