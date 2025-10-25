"""
Production Configuration for AI Agent
Handles secure configuration, environment variables, and production settings
"""

import os
import secrets
from datetime import timedelta
from typing import Optional

class ProductionConfig:
    """Production configuration with security best practices"""
    
    # Security Configuration
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    
    # Session Configuration
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_SECURE = True  # HTTPS only
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security Headers
    SECURITY_HEADERS = {
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:;"
    }
    
    # Database Configuration
    DATABASE_URL = os.environ.get('DATABASE_URL', '/tmp/payments.db')
    BACKUP_INTERVAL_HOURS = int(os.environ.get('BACKUP_INTERVAL_HOURS', '6'))
    
    # External API Configuration
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL', 'http://192.168.86.53:11434')
    OLLAMA_MODEL = os.environ.get('OLLAMA_MODEL', 'llama3:latest')
    
    # Rate Limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', '/var/log/ai-agent/app.log')
    
    # Authentication Configuration
    AUTH_ENABLED = os.environ.get('AUTH_ENABLED', 'true').lower() == 'true'
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or secrets.token_hex(32)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    
    # Admin Configuration
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
    ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')  # Should be bcrypt hash
    
    # Email Configuration
    NOTIFICATION_EMAIL_ENABLED = os.environ.get('NOTIFICATION_EMAIL_ENABLED', 'false').lower() == 'true'
    SMTP_SERVER = os.environ.get('SMTP_SERVER')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USERNAME = os.environ.get('SMTP_USERNAME')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')
    NOTIFICATION_EMAIL_FROM = os.environ.get('NOTIFICATION_EMAIL_FROM')
    NOTIFICATION_EMAIL_TO = os.environ.get('NOTIFICATION_EMAIL_TO')
    
    # Performance Configuration
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    
    @classmethod
    def validate_config(cls):
        """Validate required configuration is present"""
        errors = []
        
        if cls.AUTH_ENABLED and not cls.ADMIN_PASSWORD_HASH:
            errors.append("ADMIN_PASSWORD_HASH is required when AUTH_ENABLED=true")
        
        if cls.NOTIFICATION_EMAIL_ENABLED:
            required_email_vars = ['SMTP_SERVER', 'SMTP_USERNAME', 'SMTP_PASSWORD', 
                                 'NOTIFICATION_EMAIL_FROM', 'NOTIFICATION_EMAIL_TO']
            for var in required_email_vars:
                if not getattr(cls, var):
                    errors.append(f"{var} is required when NOTIFICATION_EMAIL_ENABLED=true")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(errors))
        
        return True

class DevelopmentConfig:
    """Development configuration - less secure, more convenient"""
    
    SECRET_KEY = 'dev-secret-key-not-for-production'
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    SESSION_COOKIE_HTTPONLY = True
    
    DATABASE_URL = '/tmp/payments_dev.db'
    LOG_LEVEL = 'DEBUG'
    AUTH_ENABLED = False
    
    OLLAMA_BASE_URL = 'http://192.168.86.53:11434'
    OLLAMA_MODEL = 'llama3:latest'

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    
    if env == 'production':
        config = ProductionConfig()
        config.validate_config()
        return config
    else:
        return DevelopmentConfig()


