
from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, send_file
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timezone
import os
from pathlib import Path

from app import db, csrf
from app.models import Project, TestScript, ExecutionResult, ProjectMember, User, ScriptVersion
from app.models import ExecutionStatus
from app.auth import project_access_required
from app.utils.security import (
    sanitize_input,
    validate_project_name, validate_script_name, generate_csrf_token
)
from app.utils.fs import ensure_directory, sanitize_filename, safe_path_join, read_file_safely, write_file_safely
from app.config import Config

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

bp = Blueprint('projects', __name__)

# Endpoint to fetch a fresh CSRF token (AJAX)
@bp.route('/get_csrf_token', methods=['GET'])
@login_required
def get_csrf_token():
    token = generate_csrf_token()
    session['csrf_token'] = token
    return jsonify({'csrf_token': token})

# Simple forms for CSRF protection only
class DeleteForm(FlaskForm):
    pass

class UploadForm(FlaskForm):
    pass

class DeleteProjectForm(FlaskForm):
    pass



class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired()])
    description = StringField('Description')
    base_url = StringField('Base URL')
    submit = SubmitField('Create Project')

@bp.route('/')
@login_required
def list_projects():
    """List all projects accessible to the current user"""
    if current_user.has_role('Admin'):
        # Admin can see all projects
        projects = Project.query.order_by(Project.updated_at.desc()).all()
    else:
        # Get projects owned by user or where user is a member
        owned_projects = Project.query.filter_by(owner_id=current_user.id).all()
        
        member_projects = db.session.query(Project).join(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(ProjectMember.user_id == current_user.id).all()
        
        # Combine and remove duplicates
        project_ids = set()
        projects = []
        
        for project in owned_projects + member_projects:
            if project.id not in project_ids:
                projects.append(project)
                project_ids.add(project.id)
        
        # Sort by updated_at desc
        projects.sort(key=lambda p: p.updated_at, reverse=True)
    
    # Get project statistics
    project_stats = {}
    for project in projects:
        stats = {
            'total_scripts': len(project.test_scripts),
            'converted_scripts': sum(1 for s in project.test_scripts if s.conversion_status == 'completed'),
            'last_execution': None,
            'last_execution_status': None
        }
        
        # Get last execution
        last_execution = ExecutionResult.query.filter_by(
            project_id=project.id
        ).order_by(ExecutionResult.started_at.desc()).first()
        
        if last_execution:
            stats['last_execution'] = last_execution.started_at
            stats['last_execution_status'] = last_execution.status
        
        project_stats[project.id] = stats
    
    return render_template('projects.html',
                         title='Projects',
                         projects=projects,
                         project_stats=project_stats)

@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create a new project"""
    form = ProjectForm()
    if form.validate_on_submit():
        name = sanitize_input(form.name.data.strip())
        description = sanitize_input(form.description.data.strip())
        base_url = sanitize_input(form.base_url.data.strip())
        
        # Validate input
        name_validation = validate_project_name(name)
        if not name_validation['valid']:
            flash(name_validation['message'], 'danger')
            return render_template('create_project.html', title='Create Project', form=form)
        
        # Validate base URL if provided
        if base_url:
            from app.utils.security import validate_url
            if not validate_url(base_url):
                flash('Please enter a valid base URL (http:// or https://).', 'danger')
                return render_template('create_project.html', title='Create Project', form=form)
        
        # Check for duplicate project names for this user
        existing_project = Project.query.filter_by(
            name=name,
            owner_id=current_user.id
        ).first()
        
        if existing_project:
            flash('You already have a project with this name.', 'danger')
            return render_template('create_project.html', title='Create Project', form=form)
        
        # Create project
        try:
            project = Project(
                name=name,
                description=description,
                base_url=base_url if base_url else None,
                owner_id=current_user.id
            )
            
            db.session.add(project)
            db.session.commit()
            
            # Create project directories
            project_name_safe = sanitize_filename(name)
            playwright_dir = Config.TEST_APP_ROOT / 'playwright_scripts' / project_name_safe
            robot_dir = Config.TEST_APP_ROOT / 'robot_scripts' / project_name_safe
            
            ensure_directory(playwright_dir)
            ensure_directory(robot_dir)
            
            flash(f'Project "{name}" created successfully!', 'success')
            return redirect(url_for('projects.detail', id=project.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to create project. Please try again.', 'danger')
            return render_template('create_project.html', title='Create Project', form=form)
    
    return render_template('create_project.html', title='Create Project', form=form)

@bp.route('/<int:id>')
@login_required
@project_access_required()
def detail(id):
    """Project detail page"""
    project = Project.query.get_or_404(id)
    
    # Get project scripts with execution statistics
    scripts_with_stats = []
    
    for script in project.test_scripts:
        # Get last execution for this script
        last_execution = ExecutionResult.query.filter_by(
            script_id=script.id
        ).order_by(ExecutionResult.started_at.desc()).first()
        
        # Get execution count and pass rate
        total_executions = ExecutionResult.query.filter_by(script_id=script.id).count()
        
        passed_executions = ExecutionResult.query.filter_by(
            script_id=script.id,
            status=ExecutionStatus.PASSED
        ).count()
        
        pass_rate = (passed_executions / total_executions * 100) if total_executions > 0 else 0
        
        scripts_with_stats.append({
            'script': script,
            'last_execution': last_execution,
            'total_executions': total_executions,
            'pass_rate': round(pass_rate, 1)
        })
    
    # Sort by last execution date (most recent first)
    def get_started_at(execution):
        if execution and execution.started_at:
            dt = execution.started_at
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        return datetime.min.replace(tzinfo=timezone.utc)

    scripts_with_stats.sort(
        key=lambda x: get_started_at(x['last_execution']),
        reverse=True
    )
    
    # Get project members
    members = db.session.query(ProjectMember, User).join(
        User, ProjectMember.user_id == User.id
    ).filter(ProjectMember.project_id == project.id).all()
    
    # Check user permissions
    can_edit = current_user.can_edit_project(project)
    
    # Pass CSRF-protected forms to template
    delete_form = DeleteForm()
    upload_form = UploadForm()
    delete_project_form = DeleteProjectForm()
    return render_template('project_detail.html',
                         title=f'Project: {project.name}',
                         project=project,
                         scripts_with_stats=scripts_with_stats,
                         members=members,
                         can_edit=can_edit,
                         delete_form=delete_form,
                         upload_form=upload_form,
                         delete_project_form=delete_project_form)

@bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@project_access_required(edit_required=True)
def edit_project(id):
    """Edit project details"""
    project = Project.query.get_or_404(id)
    form = ProjectForm(obj=project)
    
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', '').strip())
        description = sanitize_input(request.form.get('description', '').strip())
        base_url = sanitize_input(request.form.get('base_url', '').strip())
        
        # Validate input
        name_validation = validate_project_name(name)
        if not name_validation['valid']:
            flash(name_validation['message'], 'danger')
            return render_template('edit_project.html',
                                 title='Edit Project',
                                 project=project,
                                 name=name, description=description, base_url=base_url)
        
        # Validate base URL if provided
        if base_url:
            from app.utils.security import validate_url
            if not validate_url(base_url):
                flash('Please enter a valid base URL.', 'danger')
                return render_template('edit_project.html',
                                     title='Edit Project',
                                     project=project,
                                     name=name, description=description, base_url=base_url)
        
        # Check for duplicate names (excluding current project)
        existing_project = Project.query.filter(
            Project.name == name,
            Project.owner_id == current_user.id,
            Project.id != project.id
        ).first()
        
        if existing_project:
            flash('You already have another project with this name.', 'danger')
            return render_template('edit_project.html',
                                 title='Edit Project',
                                 project=project,
                                 name='', description=description, base_url=base_url)
        
        # Update project
        try:
            project.name = name
            project.description = description
            project.base_url = base_url if base_url else None
            project.updated_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            flash('Project updated successfully!', 'success')
            return redirect(url_for('projects.detail', id=project.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to update project. Please try again.', 'danger')
    
    return render_template('edit_project.html',
                         title='Edit Project',
                         project=project,
                         form=form)

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
@project_access_required(edit_required=True)
def delete_project(id):
    """Delete a project"""
    project = Project.query.get_or_404(id)
    
    # Only owner or admin can delete
    if project.owner_id != current_user.id and not current_user.has_role('Admin'):
        flash('Only the project owner can delete the project.', 'danger')
        return redirect(url_for('projects.detail', id=id))
    
    try:
        project_name = project.name
        
        # Delete associated files (scripts, results, videos)
        project_name_safe = sanitize_filename(project_name)
        
        # Clean up directories
        from app.utils.fs import clean_old_files
        import shutil
        
        directories_to_clean = [
            Config.TEST_APP_ROOT / 'playwright_scripts' / project_name_safe,
            Config.TEST_APP_ROOT / 'robot_scripts' / project_name_safe,
            Config.TEST_APP_ROOT / 'execution_videos' / project_name_safe,
            Config.TEST_APP_ROOT / 'results' / project_name_safe
        ]
        
        for directory in directories_to_clean:
            if directory.exists():
                shutil.rmtree(directory, ignore_errors=True)
        
        # Delete from database (cascade will handle related records)
        db.session.delete(project)
        db.session.commit()
        
        flash(f'Project "{project_name}" has been deleted.', 'success')
        return redirect(url_for('projects.list_projects'))
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete project. Please try again.', 'danger')
        return redirect(url_for('projects.detail', id=id))

@bp.route('/<int:id>/scripts/<int:script_id>')
@login_required
@project_access_required()
def script_detail(id, script_id):
    """View script details"""
    project = Project.query.get_or_404(id)
    script = TestScript.query.filter_by(id=script_id, project_id=project.id).first_or_404()
    
    # Get script execution history
    executions = ExecutionResult.query.filter_by(
        script_id=script.id
    ).order_by(ExecutionResult.started_at.desc()).limit(20).all()
    
    # Get script versions
    versions = ScriptVersion.query.filter_by(
        script_id=script.id
    ).order_by(ScriptVersion.version_number.desc()).all()
    
    # Read current Robot script content if available
    robot_content = ""
    if script.robot_script_path and Path(script.robot_script_path).exists():
        result = read_file_safely(script.robot_script_path)
        if result['success']:
            robot_content = result['content']
    
    return render_template('script_detail.html',
                         title=f'Script: {script.name}',
                         project=project,
                         script=script,
                         executions=executions,
                         versions=versions,
                         robot_content=robot_content,
                         can_edit=current_user.can_edit_project(project))

@bp.route('/<int:id>/scripts/<int:script_id>/edit', methods=['GET', 'POST'])
@csrf.exempt
@login_required
@project_access_required(edit_required=True)
def edit_script(id, script_id):
    """Edit script content"""
    project = Project.query.get_or_404(id)
    script = TestScript.query.filter_by(id=script_id, project_id=project.id).first_or_404()

    from app.utils.security import generate_csrf_token, validate_csrf_token
    if request.method == 'POST':
        csrf_token = request.form.get('csrf_token')
        session_token = session.get('csrf_token')
        if not validate_csrf_token(csrf_token, session_token):
            flash('Invalid CSRF token. Please refresh the page and try again.', 'danger')
            return redirect(url_for('projects.edit_script', id=id, script_id=script_id))

        # Regenerate CSRF token after POST to prevent replay
        session['csrf_token'] = generate_csrf_token()

        action = request.form.get('action')

        if action == 'update_metadata':
            name = sanitize_input(request.form.get('name', '').strip())
            description = sanitize_input(request.form.get('description', '').strip())
            tags = sanitize_input(request.form.get('tags', '').strip())

            # Validate script name
            name_validation = validate_script_name(name)
            if not name_validation['valid']:
                flash(name_validation['message'], 'danger')
                return redirect(url_for('projects.edit_script', id=id, script_id=script_id))

            # Update script metadata
            script.name = name
            script.description = description
            script.tags = tags
            script.updated_at = datetime.now(timezone.utc)

            db.session.commit()
            flash('Script metadata updated successfully!', 'success')

        elif action == 'update_content':
            robot_content = request.form.get('robot_content', '')
            # Normalize line endings and remove trailing blank lines
            robot_content = robot_content.replace('\r\n', '\n').replace('\r', '\n')
            robot_content = '\n'.join([line.rstrip() for line in robot_content.split('\n')])
            # Remove trailing blank lines
            while robot_content.endswith('\n'):
                robot_content = robot_content[:-1]

            if not script.robot_script_path:
                # Create new robot script file
                project_name_safe = sanitize_filename(project.name)
                script_name_safe = sanitize_filename(script.name)

                robot_dir = Config.TEST_APP_ROOT / 'robot_scripts' / project_name_safe
                ensure_directory(robot_dir)

                robot_file = robot_dir / f"{script_name_safe}.robot"
                script.robot_script_path = str(robot_file)

            # Save current version before updating
            if Path(script.robot_script_path).exists():
                current_content_result = read_file_safely(script.robot_script_path)
                if current_content_result['success']:
                    # Get next version number
                    max_version = db.session.query(
                        db.func.max(ScriptVersion.version_number)
                    ).filter_by(script_id=script.id).scalar() or 0

                    version = ScriptVersion(
                        script_id=script.id,
                        version_number=max_version + 1,
                        robot_content=current_content_result['content'],
                        created_by_id=current_user.id
                    )
                    db.session.add(version)

            # Write new content
            write_result = write_file_safely(script.robot_script_path, robot_content)

            if write_result['success']:
                script.updated_at = datetime.now(timezone.utc)
                script.conversion_status = 'completed'  # Mark as manually updated
                db.session.commit()
                flash('Script content updated successfully!', 'success')
            else:
                db.session.rollback()
                flash(f'Failed to save script: {write_result["error"]}', 'danger')

        return redirect(url_for('projects.edit_script', id=id, script_id=script_id))

    # GET request: generate and store CSRF token
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token

    # Read current content
    robot_content = ""
    if script.robot_script_path and Path(script.robot_script_path).exists():
        result = read_file_safely(script.robot_script_path)
        if result['success']:
            robot_content = result['content']

    return render_template('script_edit.html',
                         title=f'Edit Script: {script.name}',
                         project=project,
                         script=script,
                         robot_content=robot_content,
                         csrf_token=csrf_token)

@bp.route('/<int:id>/scripts/<int:script_id>/delete', methods=['POST'])
@login_required
@project_access_required(edit_required=True)
def delete_script(id, script_id):
    """Delete a test script"""
    project = Project.query.get_or_404(id)
    script = TestScript.query.filter_by(id=script_id, project_id=project.id).first_or_404()
    

    
    try:
        script_name = script.name
        
        # Delete associated files
        if script.playwright_script_path and Path(script.playwright_script_path).exists():
            Path(script.playwright_script_path).unlink()
        
        if script.robot_script_path and Path(script.robot_script_path).exists():
            Path(script.robot_script_path).unlink()
        
        # Delete from database (cascade will handle execution results and versions)
        db.session.delete(script)
        db.session.commit()
        
        flash(f'Script "{script_name}" has been deleted.', 'success')
        return redirect(url_for('projects.detail', id=id))
        
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete script. Please try again.', 'danger')
        return redirect(url_for('projects.script_detail', id=id, script_id=script_id))

@bp.route('/<int:id>/upload-script', methods=['POST'])
@login_required
@project_access_required(edit_required=True)
def upload_script(id):
    """Upload a Robot Framework script to the project"""
    project = Project.query.get_or_404(id)
    

    
    if 'robot_file' not in request.files:
        flash('No file selected.', 'danger')
        return redirect(url_for('projects.detail', id=id))
    
    file = request.files['robot_file']
    
    if file.filename == '':
        flash('No file selected.', 'danger')
        return redirect(url_for('projects.detail', id=id))
    
    # Validate file extension
    if not file.filename.lower().endswith('.robot'):
        flash('Please upload a .robot file.', 'danger')
        return redirect(url_for('projects.detail', id=id))
    
    try:
        # Read file content
        content = file.read().decode('utf-8')
        
        # Generate script name from filename
        script_name = Path(file.filename).stem
        script_name = sanitize_input(script_name)
        
        # Check for duplicate script names
        counter = 1
        original_name = script_name
        while TestScript.query.filter_by(name=script_name, project_id=project.id).first():
            script_name = f"{original_name}_{counter}"
            counter += 1
        
        # Create script record
        script = TestScript(
            name=script_name,
            description=f"Uploaded from {file.filename}",
            project_id=project.id,
            created_by_id=current_user.id,
            conversion_status='completed'
        )
        
        db.session.add(script)
        db.session.flush()  # Get script ID
        
        # Save file
        project_name_safe = sanitize_filename(project.name)
        script_name_safe = sanitize_filename(script_name)
        
        robot_dir = Config.TEST_APP_ROOT / 'robot_scripts' / project_name_safe
        ensure_directory(robot_dir)
        
        robot_file_path = robot_dir / f"{script_name_safe}.robot"
        
        write_result = write_file_safely(robot_file_path, content)
        
        if write_result['success']:
            script.robot_script_path = str(robot_file_path)
            db.session.commit()
            
            flash(f'Script "{script_name}" uploaded successfully!', 'success')
        else:
            db.session.rollback()
            flash(f'Failed to save uploaded file: {write_result["error"]}', 'danger')
        
    except UnicodeDecodeError:
        flash('Invalid file encoding. Please upload a UTF-8 encoded .robot file.', 'danger')
    except Exception as e:
        db.session.rollback()
        flash('Failed to upload script. Please try again.', 'danger')
    
    return redirect(url_for('projects.detail', id=id))

@bp.route('/<int:id>/scripts/<int:script_id>/download')
@login_required
@project_access_required()
def download_script(id, script_id):
    """Download a Robot Framework script"""
    project = Project.query.get_or_404(id)
    script = TestScript.query.filter_by(id=script_id, project_id=project.id).first_or_404()
    
    if not script.robot_script_path or not Path(script.robot_script_path).exists():
        flash('Script file not found.', 'danger')
        return redirect(url_for('projects.script_detail', id=id, script_id=script_id))
    
    return send_file(
        script.robot_script_path,
        as_attachment=True,
        download_name=f"{sanitize_filename(script.name)}.robot",
        mimetype='text/plain'
    )
    
    return redirect(url_for('projects.detail', id=id))

@bp.route('/<int:id>/scripts/<int:script_id>/download')
@login_required
@project_access_required()
def download_script_file(id, script_id):
    """Download a Robot Framework script"""
    project = Project.query.get_or_404(id)
    script = TestScript.query.filter_by(id=script_id, project_id=project.id).first_or_404()
    
    if not script.robot_script_path or not Path(script.robot_script_path).exists():
        flash('Script file not found.', 'danger')
        return redirect(url_for('projects.script_detail', id=id, script_id=script_id))
    
    return send_file(
        script.robot_script_path,
        as_attachment=True,
        download_name=f"{sanitize_filename(script.name)}.robot",
        mimetype='text/plain'
    )
