from functools import wraps
from flask import redirect, url_for, flash, request
from flask_login import current_user

def role_required(role_name):
    """Decorator to require specific role for access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            if not current_user.has_role(role_name) and not current_user.has_role('Admin'):
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def project_access_required(edit_required=False):
    """Decorator to require project access"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            
            project_id = kwargs.get('project_id') or request.view_args.get('project_id')
            if project_id:
                from app.models import Project
                project = Project.query.get_or_404(project_id)
                
                if edit_required and not current_user.can_edit_project(project):
                    flash('You do not have edit permission for this project.', 'danger')
                    return redirect(url_for('projects.detail', id=project_id))
                elif not current_user.can_access_project(project):
                    flash('You do not have access to this project.', 'danger')
                    return redirect(url_for('main.dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
