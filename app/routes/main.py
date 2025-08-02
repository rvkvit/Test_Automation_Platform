from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from app.models import Project, TestScript, ExecutionResult, ExecutionStatus
from app import db

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
        # Get basic counts
        if current_user.has_role('Admin'):
            project_count = Project.query.count()
            script_count = TestScript.query.count()
            execution_count = ExecutionResult.query.count()
            recent_executions = ExecutionResult.query.order_by(ExecutionResult.started_at.desc()).limit(10).all()
        else:
            # User-specific data
            user_projects = Project.query.filter_by(owner_id=current_user.id).all()
            project_count = len(user_projects)
            script_count = sum(len(p.scripts) for p in user_projects)
            execution_count = ExecutionResult.query.filter(ExecutionResult.project_id.in_([p.id for p in user_projects])).count()
            recent_executions = ExecutionResult.query.filter(ExecutionResult.project_id.in_([p.id for p in user_projects])).order_by(ExecutionResult.started_at.desc()).limit(10).all()
        
        # Calculate success rate
        if execution_count > 0:
            if current_user.has_role('Admin'):
                passed_count = ExecutionResult.query.filter_by(status=ExecutionStatus.PASSED).count()
            else:
                passed_count = ExecutionResult.query.filter(
                    ExecutionResult.project_id.in_([p.id for p in user_projects]),
                    ExecutionResult.status == ExecutionStatus.PASSED
                ).count()
            success_rate = round((passed_count / execution_count) * 100, 1)
        else:
            success_rate = 0
        
        return render_template('dashboard.html', 
                             title='Dashboard',
                             project_count=project_count,
                             script_count=script_count,
                             execution_count=execution_count,
                             success_rate=success_rate,
                             recent_executions=recent_executions)
    except Exception as e:
        # Handle any errors gracefully
        import logging
        logging.error(f"Dashboard error: {str(e)}")
        
        return render_template('dashboard.html', 
                             title='Dashboard',
                             project_count=0,
                             script_count=0,
                             execution_count=0,
                             success_rate=0,
                             recent_executions=[],
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
