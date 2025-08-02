import secrets
import string
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin
from flask import request

def sanitize_input(text):
    """Sanitize user input to prevent basic injection attacks"""
    if not text:
        return ''
    # Remove null bytes and control characters
    text = text.replace('\x00', '').replace('\r', '').replace('\n', ' ')
    # Strip leading/trailing whitespace
    return text.strip()

def generate_csrf_token():
    """Generate a CSRF token"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token, session_token):
    """Validate CSRF token"""
    if not token or not session_token:
        return False
    return secrets.compare_digest(token, session_token)

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_username(username):
    """Validate username format"""
    if not username or len(username) < 3 or len(username) > 30:
        return False
    pattern = r'^[a-zA-Z0-9_-]+$'
    return re.match(pattern, username) is not None

def generate_invitation_token():
    """Generate a secure invitation token"""
    return secrets.token_urlsafe(32)

def generate_secure_token():
    """Generate a secure token"""
    return secrets.token_urlsafe(32)

def is_safe_url(target):
    """Check if a URL is safe for redirect"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

import hashlib
import hmac
import logging
from datetime import timedelta, timezone
from urllib.parse import quote, unquote

logger = logging.getLogger(__name__)

def generate_secure_token(length=32):
    """Generate a cryptographically secure random token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def hash_password_simple(password):
    """Simple password hashing for demonstration (use proper hashing in production)"""
    salt = secrets.token_hex(16)
    password_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${password_hash.hex()}"

def verify_password_simple(password, hashed):
    """Verify password against simple hash"""
    try:
        salt, password_hash = hashed.split('$')
        computed_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hmac.compare_digest(password_hash, computed_hash.hex())
    except:
        return False

def validate_password_strength(password):
    """
    Validate password strength
    Returns dict with validation result and feedback
    """
    if not password:
        return {'valid': False, 'message': 'Password is required'}
    
    issues = []
    
    # Minimum length
    if len(password) < 8:
        issues.append('at least 8 characters')
    
    # Maximum length (prevent DoS)
    if len(password) > 128:
        issues.append('no more than 128 characters')
    
    # Character requirements
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in '!@#$%^&*(),.?":{}|<>' for c in password)
    
    if not has_upper:
        issues.append('at least one uppercase letter')
    if not has_lower:
        issues.append('at least one lowercase letter')
    if not has_digit:
        issues.append('at least one digit')
    if not has_special:
        issues.append('at least one special character')
    
    # Common password check (basic)
    common_passwords = [
        'password', '123456', '123456789', 'qwerty', 'abc123',
        'password123', '111111', '123123', 'admin', 'letmein'
    ]
    
    if password.lower() in common_passwords:
        issues.append('must not be a common password')
    
    if issues:
        return {
            'valid': False,
            'message': f'Password must have {", ".join(issues)}'
        }
    
    return {'valid': True, 'message': 'Password is strong'}

def validate_url(url, allowed_schemes=None):
    """
    Validate URL format and scheme
    """
    if not url:
        return False
    
    if allowed_schemes is None:
        allowed_schemes = ['http', 'https']
    
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme.lower() not in allowed_schemes:
            return False
        
        # Must have netloc (domain)
        if not parsed.netloc:
            return False
        
        return True
        
    except Exception:
        return False

def is_token_expired(created_at, expires_in_hours=72):
    """Check if a token has expired"""
    if not created_at:
        return True
    
    expiry_time = created_at + timedelta(hours=expires_in_hours)
    return datetime.now(timezone.utc) > expiry_time.replace(tzinfo=timezone.utc)

def secure_filename_validation(filename):
    """
    Validate uploaded filename for security
    Returns tuple (is_valid, sanitized_name)
    """
    if not filename:
        return False, ""
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Check for dangerous patterns
    dangerous_patterns = [
        r'\.\.', r'__', r'^\.',  # Path traversal and hidden files
        r'[<>:"|?*]',  # Invalid filename characters
        r'^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)',  # Windows reserved names
    ]
    
    for pattern in dangerous_patterns:
        if re.search(pattern, filename, re.IGNORECASE):
            return False, ""
    
    # Sanitize the filename
    sanitized = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Ensure it's not empty after sanitization
    if not sanitized or sanitized.startswith('.'):
        return False, ""
    
    # Limit length
    if len(sanitized) > 255:
        sanitized = sanitized[:255]
    
    return True, sanitized

def rate_limit_key(user_id, action, window_minutes=15):
    """
    Generate a rate limiting key for a user action
    """
    timestamp = int(datetime.now().timestamp() / (window_minutes * 60))
    return f"rate_limit:{user_id}:{action}:{timestamp}"

def validate_project_name(name):
    """Validate project name"""
    if not name:
        return {'valid': False, 'message': 'Project name is required'}
    
    if len(name) < 3:
        return {'valid': False, 'message': 'Project name must be at least 3 characters'}
    
    if len(name) > 100:
        return {'valid': False, 'message': 'Project name must be less than 100 characters'}
    
    # Allow alphanumeric, spaces, dash, underscore
    if not re.match(r'^[a-zA-Z0-9\s_-]+$', name):
        return {'valid': False, 'message': 'Project name can only contain letters, numbers, spaces, dashes, and underscores'}
    
    return {'valid': True}

def validate_script_name(name):
    """Validate test script name"""
    if not name:
        return {'valid': False, 'message': 'Script name is required'}
    
    if len(name) < 3:
        return {'valid': False, 'message': 'Script name must be at least 3 characters'}
    
    if len(name) > 100:
        return {'valid': False, 'message': 'Script name must be less than 100 characters'}
    
    # Allow alphanumeric, spaces, dash, underscore
    if not re.match(r'^[a-zA-Z0-9\s_-]+$', name):
        return {'valid': False, 'message': 'Script name can only contain letters, numbers, spaces, dashes, and underscores'}
    
    return {'valid': True}

def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    
    return (str(text)
           .replace('&', '&amp;')
           .replace('<', '&lt;')
           .replace('>', '&gt;')
           .replace('"', '&quot;')
           .replace("'", '&#x27;'))

def create_secure_headers():
    """Create security headers for HTTP responses"""
    return {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net cdnjs.cloudflare.com; img-src 'self' data:; font-src 'self' cdn.jsdelivr.net cdnjs.cloudflare.com;"
    }

class SecurityMiddleware:
    """Basic security middleware for Flask"""
    
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        @app.after_request
        def add_security_headers(response):
            headers = create_secure_headers()
            for header, value in headers.items():
                response.headers[header] = value
            return response