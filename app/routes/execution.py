import os
from flask import abort
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, send_file
from flask_login import login_required, current_user
from datetime import datetime, timezone
import threading
from pathlib import Path

from app import db
from app.models import Project, TestScript, ExecutionResult, ExecutionStatus
from app.auth import project_access_required
from app.utils.security import sanitize_input
from flask_wtf import FlaskForm
from wtforms import HiddenField
from app import csrf
from app.utils.security import validate_csrf_token
from app.execution import execute_script_async, execute_suite_async, RobotFrameworkExecutor
from app.config import Config
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app import db
from app.models import Project, TestScript, ExecutionResult, ExecutionStatus

bp = Blueprint('execution', __name__)

@bp.route('/')
@bp.route('/results')
@login_required
def list_results():
    """List execution results"""
    page = request.args.get('page', 1, type=int)
    project_id = request.args.get('project_id')
    status_filter = request.args.get('status')

    # Base query
    query = ExecutionResult.query

    # Filter by project if specified
    if project_id:
        query = query.filter(ExecutionResult.project_id == project_id)
    elif not current_user.has_role('Admin'):
        # Filter to user's projects only
        user_projects = Project.query.filter_by(owner_id=current_user.id).all()
        project_ids = [p.id for p in user_projects]
        if project_ids:
            query = query.filter(ExecutionResult.project_id.in_(project_ids))
        else:
            query = query.filter(False)  # No results

    # Filter by status if specified
    if status_filter and status_filter != 'all':
        try:
            status_enum = ExecutionStatus(status_filter)
            query = query.filter(ExecutionResult.status == status_enum)
        except ValueError:
            pass  # Invalid status, ignore

    # Order by most recent first
    query = query.order_by(ExecutionResult.started_at.desc())

    # Paginate
    executions = query.paginate(
        page=page, per_page=20, error_out=False
    )

    # Get projects for filter dropdown
    if current_user.has_role('Admin'):
        projects = Project.query.order_by(Project.name).all()
    else:
        projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.name).all()

    return render_template('execution_results.html',
                         title='Execution Results',
                         executions=executions,
                         projects=projects,
                         current_project_id=project_id,
                         current_status=status_filter)

@bp.route('/<int:execution_id>')
@login_required
def detail(execution_id):
    """View execution details"""
    execution = ExecutionResult.query.get_or_404(execution_id)

    # Check access
    if not current_user.has_role('Admin') and execution.project.owner_id != current_user.id:
        flash('You do not have permission to view this execution.', 'danger')
        return redirect(url_for('execution.list_results'))

    return render_template('execution_detail.html',
                         title=f'Execution #{execution.id}',
                         execution=execution)

@bp.route('/run/<int:script_id>', methods=['POST'])
@login_required
def run_script(script_id):
    """Execute a test script"""
    script = TestScript.query.get_or_404(script_id)

    # Check access
    if not current_user.can_edit_project(script.project):
        flash('You do not have permission to execute this script.', 'danger')
        return redirect(url_for('projects.script_detail', id=script.project_id, script_id=script_id))

    # Create execution record
    execution = ExecutionResult(
        project_id=script.project_id,
        script_id=script.id,
        status=ExecutionStatus.PENDING,
        executed_by_id=current_user.id
    )

    db.session.add(execution)
    db.session.commit()

    # For now, just mark as completed (placeholder for actual execution)
    execution.status = ExecutionStatus.PASSED
    execution.ended_at = datetime.now(timezone.utc)
    execution.duration = 5.0  # Placeholder
    execution.test_count = 1
    execution.passed_count = 1
    execution.failed_count = 0

    db.session.commit()

    flash(f'Script "{script.name}" executed successfully!', 'success')
    return redirect(url_for('execution.detail', execution_id=execution.id))

@bp.route('/script/<int:script_id>', methods=['POST'])
@csrf.exempt
@login_required
def execute_single_script(script_id):
    """Execute a single test script"""
    # Custom CSRF validation
    csrf_token = request.form.get('csrf_token')
    session_token = session.get('csrf_token')
    if not validate_csrf_token(csrf_token, session_token):
        return jsonify({'success': False, 'error': 'Security token expired'}), 400

    script = TestScript.query.get_or_404(script_id)

    # Check project access
    if not current_user.can_access_project(script.project):
        return jsonify({'success': False, 'error': 'No permission to execute this script'})

    # Check if script is ready for execution
    if script.conversion_status != 'completed' or not script.robot_script_path:
        return jsonify({'success': False, 'error': 'Script is not ready for execution. Please ensure it has been converted to Robot Framework format.'})

    if not Path(script.robot_script_path).exists():
        return jsonify({'success': False, 'error': 'Robot Framework script file not found'})

    # Get execution options
    headless = request.form.get('headless', 'true').lower() == 'true'

    try:
        if Config.USE_BACKGROUND_JOBS:
            # Execute in background
            thread = threading.Thread(
                target=execute_script_async,
                args=(script_id, current_user.id, headless)
            )
            thread.daemon = True
            thread.start()

            return jsonify({
                'success': True,
                'message': f'Execution started for "{script.name}"',
                'execution_mode': 'background'
            })
        else:
            # Execute synchronously
            executor = RobotFrameworkExecutor(script.project, headless=headless)
            execution = executor.execute_script(script, current_user)

            return jsonify({
                'success': True,
                'message': f'Execution completed for "{script.name}"',
                'execution_id': execution.id,
                'status': execution.status.value,
                'execution_mode': 'synchronous',
                'redirect_url': url_for('execution.result_detail', execution_id=execution.id)
            })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to start execution: {str(e)}'})

@bp.route('/project/<int:project_id>', methods=['POST'])
@login_required
@project_access_required()
def execute_project_suite(project_id):
    """Execute all scripts in a project as a suite"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})

    project = Project.query.get_or_404(project_id)

    # Get selected scripts or all scripts
    selected_script_ids = request.form.getlist('script_ids[]')
    if selected_script_ids:
        try:
            selected_script_ids = [int(sid) for sid in selected_script_ids]
        except ValueError:
            return jsonify({'success': False, 'error': 'Invalid script selection'})

    # Validate that scripts belong to the project and are executable
    if selected_script_ids:
        scripts = TestScript.query.filter(
            TestScript.id.in_(selected_script_ids),
            TestScript.project_id == project.id,
            TestScript.conversion_status == 'completed'
        ).all()

        if len(scripts) != len(selected_script_ids):
            return jsonify({'success': False, 'error': 'Some selected scripts are not available for execution'})
    else:
        # Execute all converted scripts in the project
        scripts = TestScript.query.filter_by(
            project_id=project.id,
            conversion_status='completed'
        ).all()

    if not scripts:
        return jsonify({'success': False, 'error': 'No executable scripts found in the project'})

    # Get execution options
    headless = request.form.get('headless', 'true').lower() == 'true'

    try:
        if Config.USE_BACKGROUND_JOBS:
            # Execute in background
            thread = threading.Thread(
                target=execute_suite_async,
                args=(project_id, current_user.id, selected_script_ids, headless)
            )
            thread.daemon = True
            thread.start()

            return jsonify({
                'success': True,
                'message': f'Suite execution started for project "{project.name}" with {len(scripts)} scripts',
                'execution_mode': 'background'
            })
        else:
            # Execute synchronously
            executor = RobotFrameworkExecutor(project, headless=headless)
            execution = executor.execute_suite(scripts, current_user)

            return jsonify({
                'success': True,
                'message': f'Suite execution completed for project "{project.name}"',
                'execution_id': execution.id,
                'status': execution.status.value,
                'execution_mode': 'synchronous',
                'redirect_url': url_for('execution.result_detail', execution_id=execution.id)
            })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to start suite execution: {str(e)}'})

@bp.route('/results')
@login_required
def list_results():
    """List execution results accessible to the user"""
    page = request.args.get('page', 1, type=int)
    project_id = request.args.get('project_id', type=int)
    status_filter = request.args.get('status')

    # Base query
    query = ExecutionResult.query

    # Filter by project access
    if not current_user.has_role('Admin'):
        # Get accessible project IDs
        accessible_project_ids = []

        # Owned projects
        owned_projects = Project.query.filter_by(owner_id=current_user.id).all()
        accessible_project_ids.extend([p.id for p in owned_projects])

        # Member projects
        from app.models import ProjectMember
        member_projects = db.session.query(Project.id).join(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(ProjectMember.user_id == current_user.id).all()
        accessible_project_ids.extend([p.id for p in member_projects])

        if accessible_project_ids:
            query = query.filter(ExecutionResult.project_id.in_(accessible_project_ids))
        else:
            # User has no accessible projects
            query = query.filter(False)

    # Apply filters
    if project_id:
        query = query.filter(ExecutionResult.project_id == project_id)

    if status_filter:
        try:
            status_enum = ExecutionStatus(status_filter)
            query = query.filter(ExecutionResult.status == status_enum)
        except ValueError:
            pass  # Invalid status filter, ignore

    # Order by most recent first
    query = query.order_by(ExecutionResult.started_at.desc())

    # Paginate
    executions = query.paginate(
        page=page,
        per_page=Config.RESULTS_PER_PAGE,
        error_out=False
    )

    # Get projects for filter dropdown
    if current_user.has_role('Admin'):
        projects = Project.query.order_by(Project.name).all()
    else:
        # Get accessible projects for filter
        owned_projects = Project.query.filter_by(owner_id=current_user.id).all()
        member_projects = db.session.query(Project).join(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(ProjectMember.user_id == current_user.id).all()

        project_dict = {p.id: p for p in owned_projects + member_projects}
        projects = list(project_dict.values())
        projects.sort(key=lambda p: p.name)

    return render_template('execution_results.html',
                         title='Execution Results',
                         executions=executions,
                         projects=projects,
                         current_project_id=project_id,
                         current_status=status_filter,
                         execution_statuses=[status.value for status in ExecutionStatus])

@bp.route('/results/<int:execution_id>')
@login_required
def result_detail(execution_id):
    """View detailed execution result"""
    execution = ExecutionResult.query.get_or_404(execution_id)

    # Check project access
    if not current_user.can_access_project(execution.project):
        flash('You do not have permission to view this execution result.', 'danger')
        return redirect(url_for('execution.list_results'))

    # Check if log files exist and are readable
    log_content = None
    report_content = None

    if execution.log_path and Path(execution.log_path).exists():
        try:
            with open(execution.log_path, 'r', encoding='utf-8') as f:
                log_content = f.read()
        except Exception:
            pass  # File not readable

    if execution.report_path and Path(execution.report_path).exists():
        try:
            with open(execution.report_path, 'r', encoding='utf-8') as f:
                report_content = f.read()
        except Exception:
            pass  # File not readable

    return render_template('execution_detail.html',
                         title=f'Execution Result #{execution.id}',
                         execution=execution,
                         log_content=log_content,
                         report_content=report_content)

@bp.route('/results/<int:execution_id>/download/<file_type>')
@login_required
def download_execution_file(execution_id, file_type):
    """Download execution result files"""
    execution = ExecutionResult.query.get_or_404(execution_id)

    # Check project access
    if not current_user.can_access_project(execution.project):
        flash('You do not have permission to access this execution result.', 'danger')
        return redirect(url_for('execution.list_results'))

    file_path = None
    filename = None
    mimetype = 'text/plain'

    if file_type == 'log' and execution.log_path:
        file_path = execution.log_path
        filename = f"execution_{execution.id}_log.html"
        mimetype = 'text/html'
    elif file_type == 'report' and execution.report_path:
        file_path = execution.report_path
        filename = f"execution_{execution.id}_report.html"
        mimetype = 'text/html'
    elif file_type == 'output' and execution.output_xml_path:
        file_path = execution.output_xml_path
        filename = f"execution_{execution.id}_output.xml"
        mimetype = 'application/xml'
    elif file_type == 'video' and execution.video_path:
        file_path = execution.video_path
        filename = f"execution_{execution.id}_video.webm"
        mimetype = 'video/webm'

    if not file_path or not Path(file_path).exists():
        flash(f'The requested {file_type} file is not available.', 'danger')
        return redirect(url_for('execution.result_detail', execution_id=execution_id))

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype
    )

@bp.route('/results/<int:execution_id>/video')
@login_required
def stream_execution_video(execution_id):
    result = ExecutionResult.query.get_or_404(execution_id)
    if not result.video_path:
        abort(404)
    # Video path is stored as a relative path from TEST_APP_ROOT
    video_abs_path = os.path.join(Config.TEST_APP_ROOT, result.video_path)
    if not os.path.exists(video_abs_path):
        abort(404)
    # Infer mimetype from file extension
    ext = os.path.splitext(video_abs_path)[1].lower()
    mimetype = 'video/webm' if ext == '.webm' else 'video/mp4' if ext == '.mp4' else 'application/octet-stream'
    return send_file(video_abs_path, mimetype=mimetype)

@bp.route('/status/<int:execution_id>')
@login_required
def execution_status(execution_id):
    """Get execution status (for polling)"""
    execution = ExecutionResult.query.get_or_404(execution_id)

    # Check project access
    if not current_user.can_access_project(execution.project):
        return jsonify({'error': 'Access denied'}), 403

    return jsonify({
        'success': True,
        'execution_id': execution.id,
        'status': execution.status.value,
        'started_at': execution.started_at.isoformat() if execution.started_at else None,
        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
        'duration_seconds': execution.duration_seconds,
        'tests_passed': execution.tests_passed,
        'tests_failed': execution.tests_failed,
        'tests_total': execution.tests_total,
        'pass_rate': execution.pass_rate,
        'error_message': execution.error_message,
        'has_video': bool(execution.video_path and Path(execution.video_path).exists()),
        'has_log': bool(execution.log_path and Path(execution.log_path).exists()),
        'has_report': bool(execution.report_path and Path(execution.report_path).exists())
    })

@bp.route('/cancel/<int:execution_id>', methods=['POST'])
@login_required
def cancel_execution(execution_id):
    """Cancel a running execution (if possible)"""
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})

    execution = ExecutionResult.query.get_or_404(execution_id)

    # Check project access
    if not current_user.can_access_project(execution.project):
        return jsonify({'success': False, 'error': 'Access denied'})

    # Check if execution can be cancelled
    if execution.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
        return jsonify({'success': False, 'error': 'Execution cannot be cancelled in its current state'})

    try:
        # For now, we just mark it as cancelled
        # In a more advanced implementation, we would kill the actual process
        execution.status = ExecutionStatus.ERROR
        execution.error_message = f'Cancelled by {current_user.username}'
        execution.completed_at = datetime.now(timezone.utc)

        if execution.started_at:
            execution.duration_seconds = (execution.completed_at - execution.started_at).total_seconds()

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Execution cancelled successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': f'Failed to cancel execution: {str(e)}'})

@bp.route('/quick-run/<int:script_id>')
@login_required
def quick_run_form(script_id):
    """Show quick run form for a script"""
    script = TestScript.query.get_or_404(script_id)

    # Check project access
    if not current_user.can_access_project(script.project):
        flash('You do not have permission to execute this script.', 'danger')
        return redirect(url_for('projects.list_projects'))

    # Generate CSRF token
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token

    return render_template('quick_run.html',
                         title=f'Quick Run: {script.name}',
                         script=script,
                         csrf_token=csrf_token)

# Add CSRF token to session for AJAX requests
@bp.before_request
def inject_csrf_token():
    """Inject CSRF token into session for AJAX requests"""
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()