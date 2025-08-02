from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from app.analytics import AnalyticsService

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    """Home page - redirect to dashboard if logged in, otherwise show login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@bp.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard with overview metrics"""
    try:
        # Get dashboard metrics
        metrics = AnalyticsService.get_dashboard_metrics()
        
        return render_template('dashboard.html', 
                             title='Dashboard',
                             metrics=metrics)
    except Exception as e:
        # Handle any errors gracefully
        import logging
        logging.error(f"Dashboard error: {str(e)}")
        
        # Fallback metrics
        fallback_metrics = {
            'total_projects': 0,
            'total_scripts': 0,
            'recent_executions': [],
            'pass_rate_7_days': 0
        }
        
        return render_template('dashboard.html', 
                             title='Dashboard',
                             metrics=fallback_metrics,
                             error='Unable to load dashboard metrics')

@bp.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    from app.utils.environment import get_system_info
    
    try:
        system_info = get_system_info()
        
        # Basic health checks
        health_status = {
            'status': 'healthy',
            'timestamp': str(datetime.now()),
            'system': system_info['runtime']['system'],
            'dependencies': system_info['dependencies']
        }
        
        # Check database connectivity
        try:
            from app import db
            db.session.execute('SELECT 1')
            health_status['database'] = 'connected'
        except Exception as e:
            health_status['database'] = f'error: {str(e)}'
            health_status['status'] = 'degraded'
        
        return health_status, 200 if health_status['status'] == 'healthy' else 503
        
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': str(datetime.now())
        }, 500

@bp.route('/system-info')
@login_required
def system_info():
    """System information page for administrators"""
    if not current_user.has_role('Admin'):
        return redirect(url_for('main.dashboard'))
    
    from app.utils.environment import get_system_info
    from datetime import datetime
    
    info = get_system_info()
    
    return render_template('system_info.html',
                         title='System Information',
                         system_info=info,
                         current_time=datetime.now())

@bp.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('errors/404.html', title='Page Not Found'), 404

@bp.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    from app import db
    db.session.rollback()
    return render_template('errors/500.html', title='Internal Server Error'), 500

@bp.errorhandler(403)
def forbidden_error(error):
    """Handle 403 errors"""
    return render_template('errors/403.html', title='Access Forbidden'), 403
