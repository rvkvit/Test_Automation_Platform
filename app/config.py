import os
from pathlib import Path

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database settings
    db_uri = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///instance/app.db")
    if db_uri.startswith("sqlite:///") and not os.path.isabs(db_uri.replace("sqlite:///", "")):
        # Convert to absolute path
        project_root = Path(__file__).parent.parent.resolve()
        rel_path = db_uri.replace("sqlite:///", "")
        abs_path = project_root / rel_path
        db_uri = f"sqlite:///{abs_path}"
    SQLALCHEMY_DATABASE_URI = db_uri
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Azure OpenAI settings
    AZURE_OPENAI_ENDPOINT = os.environ.get('AZURE_OPENAI_ENDPOINT', '')
    AZURE_OPENAI_API_KEY = os.environ.get('AZURE_OPENAI_API_KEY', '')
    AZURE_OPENAI_DEPLOYMENT = os.environ.get('AZURE_OPENAI_DEPLOYMENT', '')
    
    # Application root directory
    TEST_APP_ROOT = Path(os.environ.get('TEST_APP_ROOT') or Path(__file__).parent.parent)
    
    # Headless mode for testing
    HEADLESS = os.environ.get('HEADLESS', '1') == '1'
    
    # Email settings
    EMAIL_SENDER = os.environ.get('EMAIL_SENDER', 'noreply@localhost')
    SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')
    SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'true').lower() == 'true'
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Pagination
    RESULTS_PER_PAGE = 20
    
    # Video settings
    KEEP_VIDEO_HISTORY = os.environ.get('KEEP_VIDEO_HISTORY', 'false').lower() == 'true'
    
    # Background job settings
    USE_BACKGROUND_JOBS = os.environ.get('USE_BACKGROUND_JOBS', 'true').lower() == 'true'
    USE_BACKGROUND_JOBS = os.environ.get('USE_BACKGROUND_JOBS', 'true').lower() == 'true'
