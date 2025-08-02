from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Project, TestScript
from app.utils.security import generate_csrf_token, validate_csrf_token, sanitize_input
from flask import session

bp = Blueprint('recording', __name__)

@bp.route('/')
@login_required
def index():
    """Recording page"""
    # Get projects user can record for
    if current_user.has_role('Admin'):
        projects = Project.query.order_by(Project.name).all()
    else:
        projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.name).all()

    # Generate CSRF token
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token

    return render_template('record.html',
                         title='Record Test',
                         projects=projects,
                         csrf_token=csrf_token)

@bp.route('/start', methods=['POST'])
@login_required
def start_recording():
    """Start a new recording session"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    session_token = session.get('csrf_token')
    if not validate_csrf_token(csrf_token, session_token):
        flash('Invalid CSRF token. Please refresh the page and try again.', 'danger')
        return redirect(url_for('recording.index'))

    project_id = request.form.get('project_id')
    script_name = sanitize_input(request.form.get('script_name', '').strip())
    base_url = sanitize_input(request.form.get('base_url', '').strip())

    if not project_id or not script_name:
        flash('Project and script name are required.', 'danger')
        return redirect(url_for('recording.index'))

    # Verify project access
    project = Project.query.get_or_404(project_id)
    if not current_user.can_edit_project(project):
        flash('You do not have permission to record tests for this project.', 'danger')
        return redirect(url_for('recording.index'))

    # For now, just show a placeholder
    flash('Recording functionality will be implemented in the next phase.', 'info')
    return redirect(url_for('projects.detail', id=project_id))

@bp.route('/stop', methods=['POST'])
@login_required
def stop_recording():
    """Stop current recording session"""
    flash('Recording stopped.', 'info')
    return jsonify({'success': True})