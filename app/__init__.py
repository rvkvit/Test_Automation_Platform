import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_wtf import CSRFProtect

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()  # Add this line

def create_app():
    # Set template and static directories relative to project root
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(project_root, 'templates')
    static_dir = os.path.join(project_root, 'static')
    
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, instance_relative_config=True)
    
    # Load configuration
    from app.config import Config
    app.config.from_object(Config)
    # Set secret key for sessions and CSRF
    app.secret_key = os.environ.get("SECRET_KEY") or os.environ.get("SESSION_SECRET") or "change-this-in-production"
    app.config['WTF_CSRF_SECRET_KEY'] = app.secret_key  # Add this line
    
    # Proxy fix for reverse proxy scenarios
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)  # Add this line
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access TestCraft Pro.'
    login_manager.login_message_category = 'info'
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.main import bp as main_bp
    from app.routes.auth import bp as auth_bp
    from app.routes.projects import bp as projects_bp
    try:
        from app.routes.recording import bp as recording_bp
    except ImportError:
        recording_bp = None
    try:
        from app.routes.execution import bp as execution_bp
    except ImportError:
        execution_bp = None
    from app.routes.analytics import bp as analytics_bp
    try:
        from app.routes.team import bp as team_bp
    except ImportError:
        team_bp = None
    try:
        from app.routes.integrations import bp as integrations_bp
    except ImportError:
        integrations_bp = None

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    if recording_bp:
        app.register_blueprint(recording_bp, url_prefix='/record')
    if execution_bp:
        app.register_blueprint(execution_bp, url_prefix='/execute')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    if team_bp:
        app.register_blueprint(team_bp, url_prefix='/team')
    if integrations_bp:
        app.register_blueprint(integrations_bp, url_prefix='/integrations')
    
    # Create database tables
    with app.app_context():
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        print(f"Using database: {db_url}")
        
        # Ensure instance directory exists
        instance_dir = os.path.join(project_root, 'instance')
        os.makedirs(instance_dir, exist_ok=True)
        
        # Import models to ensure they're registered
        from app import models
        db.create_all()
        
        # Ensure default roles exist before creating admin user
        from app.models import create_default_roles, User, Role
        from werkzeug.security import generate_password_hash
        create_default_roles()
        
        # Check for existing admin user by username or email
        admin_exists = User.query.filter(
            (User.username == 'TestCraftAdmin') | (User.email == 'admin@testcraft.pro')
        ).first()
        if not admin_exists:
            admin_role = Role.query.filter_by(name='Admin').first()
            if admin_role:
                admin_user = User(
                    username='TestCraftAdmin',
                    email='admin@testcraft.pro',
                    password_hash=generate_password_hash('TestCraft2024!'),
                    role_id=admin_role.id,
                    is_active=True
                )
                db.session.add(admin_user)
                try:
                    db.session.commit()
                    print("TestCraft Pro admin user created:")
                    print("  Email: admin@testcraft.pro")
                    print("  Password: TestCraft2024!")
                except Exception as e:
                    db.session.rollback()
                    print(f"Failed to create admin user: {e}")
    
    return app
