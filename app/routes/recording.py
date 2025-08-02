from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
from app import csrf
from flask_login import login_required, current_user
from datetime import datetime, timezone
import threading
import json

from app import db
from app.models import Project, TestScript, ProjectMember, User
from app.auth import project_access_required
from app.utils.security import (
    sanitize_input, generate_csrf_token, validate_csrf_token,
    validate_script_name
)
from app.utils.fs import sanitize_filename, ensure_directory
import importlib
playback = importlib.import_module('app.playback')
from app.conversion import PlaywrightToRobotConverter
from app.config import Config

bp = Blueprint('recording', __name__)

@bp.route('/')
@login_required
def index():
    """Recording dashboard - show available projects"""
    # Get projects user can record in
    if current_user.has_role('Admin'):
        projects = Project.query.order_by(Project.name).all()
    else:
        # Get projects owned by user or where user has edit access
        owned_projects = Project.query.filter_by(owner_id=current_user.id).all()
        
        member_projects = db.session.query(Project).join(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(
            ProjectMember.user_id == current_user.id,
            ProjectMember.can_edit == True
        ).all()
        
        # Combine and deduplicate
        project_ids = set()
        projects = []
        
        for project in owned_projects + member_projects:
            if project.id not in project_ids:
                projects.append(project)
                project_ids.add(project.id)
        
        projects.sort(key=lambda p: p.name)
    
    # Set and pass CSRF token
    session['csrf_token'] = generate_csrf_token()
    csrf_token = session['csrf_token']
    return render_template('record.html',
                         title='Record New Test',
                         projects=projects,
                         csrf_token=csrf_token)

@bp.route('/start', methods=['POST'])
@csrf.exempt
@login_required
def start_recording():
    """Start a new recording session"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})
    
    # Get form data
    project_id = request.form.get('project_id')
    script_name = sanitize_input(request.form.get('script_name', '').strip())
    description = sanitize_input(request.form.get('description', '').strip())
    browser_type = request.form.get('browser_type', 'chromium')
    tags = sanitize_input(request.form.get('tags', '').strip())
    
    # Validate input
    if not project_id or not script_name:
        return jsonify({'success': False, 'error': 'Project and script name are required'})
    
    try:
        project_id = int(project_id)
    except ValueError:
        return jsonify({'success': False, 'error': 'Invalid project ID'})
    
    # Validate project access
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success': False, 'error': 'Project not found'})
    
    if not current_user.can_edit_project(project):
        return jsonify({'success': False, 'error': 'No permission to record in this project'})
    
    # Validate script name
    name_validation = validate_script_name(script_name)
    if not name_validation['valid']:
        return jsonify({'success': False, 'error': name_validation['message']})
    
    # Validate browser type
    if browser_type not in ['chromium', 'firefox', 'webkit']:
        browser_type = 'chromium'
    
    # Check for duplicate script names
    existing_script = TestScript.query.filter_by(
        name=script_name,
        project_id=project.id
    ).first()
    
    if existing_script:
        return jsonify({'success': False, 'error': 'A script with this name already exists in the project'})
    
    try:
        # Start recording session, pass base_url
        result = playback.start_recording_session(
            project_name=project.name,
            script_name=script_name,
            browser_type=browser_type,
            base_url=project.base_url
        )
        
        if result['success']:
            # Create script record in database
            script = TestScript(
                name=script_name,
                description=description,
                project_id=project.id,
                tags=tags,
                browser_type=browser_type,
                created_by_id=current_user.id,
                conversion_status='pending'
            )
            
            db.session.add(script)
            db.session.commit()
            
            # Store recording session info in session
            session['recording_session'] = {
                'project_id': project.id,
                'script_id': script.id,
                'script_name': script_name,
                'browser_type': browser_type,
                'started_at': datetime.now(timezone.utc).isoformat()
            }
            
            return jsonify({
                'success': True,
                'script_id': script.id,
                'session_key': f"{project.name}_{script_name}",
                'message': f'Recording started for "{script_name}" in {browser_type}'
            })
        else:
            return jsonify({'success': False, 'error': result['error']})
            
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to start recording: {str(e)}'})

@bp.route('/stop', methods=['POST'])
@csrf.exempt
@login_required
def stop_recording():
    """Stop the current recording session"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})
    
    # Always use DB to find active recording session for current user
    import logging
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    ten_minutes_ago = now - timedelta(minutes=10)
    scripts = TestScript.query.filter(
        TestScript.created_by_id == current_user.id,
        TestScript.conversion_status == 'pending',
        TestScript.created_at >= ten_minutes_ago
    ).order_by(TestScript.created_at.desc()).all()
    if scripts:
        script = scripts[0]
        logging.warning(f"STOP RECORDING: Using DB session for script {script.id} ({script.name}), created at {script.created_at}")
        project_id = script.project_id
        script_id = script.id
        script_name = script.name
        # Optionally reconstruct session for frontend convenience
        session['recording_session'] = {
            'project_id': project_id,
            'script_id': script_id,
            'script_name': script_name,
            'browser_type': script.browser_type,
            'started_at': script.created_at.isoformat() if hasattr(script, 'created_at') else ''
        }
    else:
        logging.warning(f"STOP RECORDING: No pending script found for user {getattr(current_user, 'id', None)} in last 10 minutes.")
        return jsonify({'success': False, 'error': 'No active recording session found. Please ensure the browser window is still open and try again.'})
    # Get project and script
    project = Project.query.get(project_id)
    script = TestScript.query.get(script_id)
    if not project or not script:
        return jsonify({'success': False, 'error': 'Project or script not found'})
    try:
        # Stop recording session
        result = playback.stop_recording_session(
            project_name=project.name,
            script_name=script_name
        )
        # If Playwright process is already stopped or missing, treat as success
        if result.get('success', False) or 'output_file' in result or script.playwright_script_path:
            # Update script with Playwright file path if available
            if 'output_file' in result:
                script.playwright_script_path = result['output_file']
                db.session.commit()
            # Only clear session if Playwright process was stopped
            session.pop('recording_session', None)
            # Start AI conversion in background
            if Config.USE_BACKGROUND_JOBS:
                thread = threading.Thread(
                    target=convert_script_async,
                    args=(script_id, current_user.id)
                )
                thread.daemon = True
                thread.start()
            else:
                # Convert synchronously (for simple environments)
                convert_result = convert_script_sync(script_id)
                if not convert_result['success']:
                    flash(f'Recording completed but conversion failed: {convert_result["error"]}', 'warning')
            return jsonify({
                'success': True,
                'script_id': script.id,
                'message': 'Recording completed successfully. AI conversion started.',
                'script_content': result.get('script_content', ''),
                'redirect_url': url_for('projects.script_detail', id=project.id, script_id=script.id)
            })
        else:
            # Do not clear session if Playwright did not stop
            return jsonify({'success': False, 'error': result.get('error', 'Failed to stop Playwright recording')})
    except Exception as e:
        # If script exists, treat as success for idempotency
        if script:
            session.pop('recording_session', None)
            return jsonify({
                'success': True,
                'script_id': script.id,
                'message': 'Recording completed (process already stopped). AI conversion started.',
                'script_content': '',
                'redirect_url': url_for('projects.script_detail', id=project.id, script_id=script.id)
            })
        return jsonify({'success': False, 'error': f'Failed to stop recording: {str(e)}'})

@bp.route('/status')
@login_required
def recording_status():
    """Get current recording status"""
    recording_session = session.get('recording_session')
    
    if not recording_session:
        return jsonify({'is_recording': False, 'status': 'no_session'})
    
    project_name = Project.query.get(recording_session['project_id']).name
    script_name = recording_session['script_name']
    
    status = playback.get_recording_status(project_name, script_name)
    
    # Add session info
    status['session_info'] = {
        'script_name': script_name,
        'browser_type': recording_session['browser_type'],
        'started_at': recording_session['started_at']
    }
    
    return jsonify(status)

@bp.route('/convert/<int:script_id>', methods=['POST'])
@csrf.exempt
@login_required
def trigger_conversion(script_id):
    """Trigger AI conversion for a script"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})
    
    script = TestScript.query.get_or_404(script_id)
    
    # Check project access
    if not current_user.can_edit_project(script.project):
        return jsonify({'success': False, 'error': 'No permission to convert this script'})
    
    # Check if script has Playwright content
    if not script.playwright_script_path:
        return jsonify({'success': False, 'error': 'No Playwright script found to convert'})
    
    try:
        if Config.USE_BACKGROUND_JOBS:
            # Start conversion in background
            thread = threading.Thread(
                target=convert_script_async,
                args=(script_id, current_user.id)
            )
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'message': 'AI conversion started in background'
            })
        else:
            # Convert synchronously
            result = convert_script_sync(script_id)
            return jsonify(result)
            
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to start conversion: {str(e)}'})

@bp.route('/conversion-status/<int:script_id>')
@login_required
def conversion_status(script_id):
    """Get conversion status for a script"""
    script = TestScript.query.get_or_404(script_id)
    
    # Check project access
    if not current_user.can_access_project(script.project):
        return jsonify({'success': False, 'error': 'No permission to view this script'})
    
    return jsonify({
        'success': True,
        'status': script.conversion_status,
        'error': script.conversion_error,
        'has_robot_script': bool(script.robot_script_path)
    })

def convert_script_sync(script_id):
    """Convert a script synchronously"""
    try:
        script = TestScript.query.get(script_id)
        if not script:
            return {'success': False, 'error': 'Script not found'}
        
        # Update status to processing
        script.conversion_status = 'processing'
        script.conversion_error = None
        db.session.commit()
        
        # Read Playwright script
        from app.utils.fs import read_file_safely
        from pathlib import Path
        
        if not script.playwright_script_path or not Path(script.playwright_script_path).exists():
            script.conversion_status = 'failed'
            script.conversion_error = 'Playwright script file not found'
            db.session.commit()
            return {'success': False, 'error': 'Playwright script file not found'}
        
        read_result = read_file_safely(script.playwright_script_path)
        if not read_result['success']:
            script.conversion_status = 'failed'
            script.conversion_error = f'Failed to read Playwright script: {read_result["error"]}'
            db.session.commit()
            return {'success': False, 'error': read_result['error']}
        
        playwright_content = read_result['content']
        
        # Prepare project metadata
        project_metadata = {
            'project_name': script.project.name,
            'base_url': script.project.base_url,
            'tags': script.get_tags_list(),
            'browser_type': script.browser_type
        }
        
        # Convert using AI
        converter = PlaywrightToRobotConverter()
        conversion_result = converter.convert_playwright_to_robot(
            playwright_content,
            project_metadata
        )
        
        if conversion_result['success']:
            # Save Robot Framework script
            project_name_safe = sanitize_filename(script.project.name)
            script_name_safe = sanitize_filename(script.name)
            
            robot_dir = Config.TEST_APP_ROOT / 'robot_scripts' / project_name_safe
            ensure_directory(robot_dir)
            
            robot_file_path = robot_dir / f"{script_name_safe}.robot"
            
            from app.utils.fs import write_file_safely
            write_result = write_file_safely(robot_file_path, conversion_result['robot_script'])
            
            if write_result['success']:
                script.robot_script_path = str(robot_file_path)
                script.conversion_status = 'completed'
                script.conversion_error = None
                db.session.commit()
                
                return {
                    'success': True,
                    'message': 'Script converted successfully',
                    'robot_script': conversion_result['robot_script'],
                    'explanation': conversion_result.get('explanation', ''),
                    'warnings': conversion_result.get('warnings', [])
                }
            else:
                script.conversion_status = 'failed'
                script.conversion_error = f'Failed to save Robot script: {write_result["error"]}'
                db.session.commit()
                return {'success': False, 'error': write_result['error']}
        else:
            script.conversion_status = 'failed'
            script.conversion_error = conversion_result['error']
            db.session.commit()
            return {'success': False, 'error': conversion_result['error']}
            
    except Exception as e:
        if 'script' in locals():
            script.conversion_status = 'failed'
            script.conversion_error = str(e)
            db.session.commit()
        return {'success': False, 'error': str(e)}

def convert_script_async(script_id, user_id):
    """Convert a script asynchronously (background task)"""
    try:
        # Create new app context for background thread
        from app import create_app
        app = create_app()
        
        with app.app_context():
            result = convert_script_sync(script_id)
            
            # Optionally send notification email
            if result['success']:
                script = TestScript.query.get(script_id)
                user = User.query.get(user_id)
                
                if script and user and user.email:
                    # Send completion notification (optional)
                    pass
            
            return result
            
    except Exception as e:
        import logging
        logging.error(f"Background conversion failed for script {script_id}: {str(e)}")
        return {'success': False, 'error': str(e)}

@bp.route('/cancel', methods=['POST'])
@csrf.exempt
@login_required
def cancel_recording():
    """Cancel current recording session"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})
    
    recording_session = session.get('recording_session')
    if not recording_session:
        return jsonify({'success': False, 'error': 'No active recording session'})
    
    try:
        project_name = Project.query.get(recording_session['project_id']).name
        script_name = recording_session['script_name']
        
        # Stop the recording process
        playback.stop_recording_session(project_name, script_name)
        
        # Clean up database record
        script = TestScript.query.get(recording_session['script_id'])
        if script:
            db.session.delete(script)
            db.session.commit()
        
        # Clear session
        session.pop('recording_session', None)
        
        return jsonify({
            'success': True,
            'message': 'Recording cancelled successfully'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to cancel recording: {str(e)}'})

# Add CSRF token to session for AJAX requests
@bp.before_request
def inject_csrf_token():
    """Inject CSRF token into session for AJAX requests"""
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()
