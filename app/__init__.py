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
    login_manager.login_message = 'Please log in to access this page.'
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
    from app.routes.recording import bp as recording_bp
    from app.routes.execution import bp as execution_bp
    from app.routes.analytics import bp as analytics_bp
    from app.routes.team import bp as team_bp
    from app.routes.integrations import bp as integrations_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(projects_bp, url_prefix='/projects')
    app.register_blueprint(recording_bp, url_prefix='/record')
    app.register_blueprint(execution_bp, url_prefix='/execute')
    app.register_blueprint(analytics_bp, url_prefix='/analytics')
    app.register_blueprint(team_bp, url_prefix='/team')
    app.register_blueprint(integrations_bp, url_prefix='/integrations')
    
    # Create database tables
    with app.app_context():
        # Ensure SQLite database directory exists (handles both relative and absolute paths)
        db_url = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_url.startswith('sqlite:///'):
            db_path = db_url.replace('sqlite:///', '')
            # Remove leading slash for relative paths like '/instance/app.db'
            if db_path.startswith('/') or db_path.startswith('\\'):
                db_path = db_path[1:]
            # If path is not absolute, make it relative to instance folder in project root
            if not os.path.isabs(db_path):
                db_path = os.path.join(project_root, db_path)
            db_dir = os.path.dirname(db_path)
            print(f"Resolved SQLite DB path: {db_path}")  # Debugging
            print(f"DB directory exists: {os.path.exists(db_dir)}, writable: {os.access(db_dir, os.W_OK)}")
            print(f"DB file exists: {os.path.exists(db_path)}, writable: {os.access(db_path, os.W_OK)}")
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir, exist_ok=True)
            # Check write permission
            if not os.access(db_dir, os.W_OK):
                print(f"ERROR: Cannot write to database directory: {db_dir}")
                import sys; sys.exit(1)
            # Try to create the database file if it does not exist
            if not os.path.exists(db_path):
                try:
                    open(db_path, 'a').close()
                    print(f"Created SQLite DB file: {db_path}")
                except Exception as e:
                    print(f"ERROR: Cannot create database file: {db_path}\n{e}")
                    import sys; sys.exit(1)
            # Final check: can we write to the database file?
            if not os.access(db_path, os.W_OK):
                print(f"ERROR: Cannot write to database file: {db_path}")
                import sys; sys.exit(1)
            # Extra: print file stats for debugging
            try:
                import stat
                st = os.stat(db_path)
                print(f"DB file stat: mode={oct(st.st_mode)}, size={st.st_size}")
            except Exception as e:
                print(f"Could not stat DB file: {e}")
        
        # Import models to ensure they're registered
        from app import models
        db.create_all()
        
        # Ensure default roles exist before creating admin user
        from app.models import create_default_roles, User, Role
        from werkzeug.security import generate_password_hash
        create_default_roles()
        
        # Check for existing admin user by username or email
        admin_exists = User.query.filter(
            (User.username == 'admin') | (User.email == 'qacoe@tcslt.com')
        ).first()
        if not admin_exists:
            admin_role = Role.query.filter_by(name='Admin').first()
            if not admin_role:
                admin_role = Role(name='Admin', description='Full system access')
                db.session.add(admin_role)
                db.session.commit()  # Commit role if newly created
            admin_user = User(
                username='QA-COE',
                email='qacoe@tcslt.com',
                password_hash=generate_password_hash('1234'),
                role=admin_role,
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("Default admin user created:")
            print("  Email: qacoe@tcslt.com")
            print("  Password: 1234")
    
    return app
