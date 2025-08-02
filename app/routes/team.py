from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, session
from flask_login import login_required, current_user
from app import db
from app.models import User, Role, Project, ProjectMember
from app.utils.security import generate_csrf_token, validate_csrf_token, sanitize_input
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin
import secrets
from app import db
from app.auth import role_required
from app.models import User, Role, Project, ProjectMember, InvitationToken
from app.utils.security import validate_csrf_token
bp = Blueprint('team', __name__)

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Team dashboard"""
    if not current_user.has_role('Admin') and not current_user.has_role('Tester'):
        flash('You do not have permission to access team management.', 'danger')
        return redirect(url_for('main.dashboard'))

    # Get team statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_projects = Project.query.count()

    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('team_dashboard.html',
                         title='Team Dashboard',
                         total_users=total_users,
                         active_users=active_users,
                         total_projects=total_projects,
                         recent_users=recent_users)

@bp.route('/users')
@login_required
def list_users():
    """List all users"""
    if not current_user.has_role('Admin'):
        flash('You do not have permission to view all users.', 'danger')
        return redirect(url_for('team.dashboard'))

    users = User.query.order_by(User.username).all()

    return render_template('team.html',
                         title='Team Members',
                         users=users)

@bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite_user():
    """Invite a new user"""
    if not current_user.has_role('Admin'):
        flash('You do not have permission to invite users.', 'danger')
        return redirect(url_for('team.dashboard'))

    if request.method == 'POST':
        # Validate CSRF token
        csrf_token = request.form.get('csrf_token')
        session_token = session.get('csrf_token')
        if not validate_csrf_token(csrf_token, session_token):
            flash('Invalid CSRF token. Please refresh the page and try again.', 'danger')
            return redirect(url_for('team.invite_user'))

        email = sanitize_input(request.form.get('email', '').strip())
        role_id = request.form.get('role_id')
        project_id = request.form.get('project_id')

        if not email or not role_id:
            flash('Email and role are required.', 'danger')
            return redirect(url_for('team.invite_user'))

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('A user with this email already exists.', 'danger')
            return redirect(url_for('team.invite_user'))

        # For now, just show a success message (email functionality would be implemented later)
        flash(f'Invitation sent to {email}. User will need to register manually for now.', 'success')
        return redirect(url_for('team.dashboard'))

    # GET request - show invitation form
    roles = Role.query.order_by(Role.name).all()
    projects = Project.query.order_by(Project.name).all()

    # Generate CSRF token
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token

    return render_template('invite.html',
                         title='Invite User',
                         roles=roles,
                         projects=projects,
                         csrf_token=csrf_token)

# Remove a user from the team (Admin only)
@bp.route('/remove_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('Admin')
def remove_user(user_id):
    user = User.query.get_or_404(user_id)
    # Prevent removing self
    if user.id == current_user.id:
        flash('You cannot remove yourself from the team.', 'warning')
        return redirect(url_for('team.dashboard'))
    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        flash('Security token expired. Please try again.', 'danger')
        return redirect(url_for('team.dashboard'))
    try:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.username} has been removed from the team.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to remove user. Please try again.', 'danger')
    return redirect(url_for('team.dashboard'))

# Change a user's role (Admin only)
@bp.route('/change_role/<int:user_id>', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    roles = Role.query.order_by(Role.name).all()
    if request.method == 'POST':
        role_id = request.form.get('role_id', type=int)
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token, session.get('csrf_token')):
            flash('Security token expired. Please try again.', 'danger')
            return redirect(url_for('team.change_role', user_id=user_id))
        role = Role.query.get(role_id)
        if not role:
            flash('Invalid role selected.', 'danger')
            return redirect(url_for('team.change_role', user_id=user_id))
        try:
            user.role = role
            db.session.commit()
            flash(f"Role for {user.username} updated to {role.name}.", 'success')
            return redirect(url_for('team.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to update role. Please try again.', 'danger')
    # GET request: show role selection form
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token
    return render_template('change_role.html', title='Change Role', user=user, roles=roles, csrf_token=csrf_token)
from app.models import User, Role, Project, ProjectMember, InvitationToken
from app.auth import role_required, project_access_required
from app.utils.security import (
    sanitize_input, generate_csrf_token, validate_csrf_token,
    validate_email, generate_invitation_token
)
from app.emailer import EmailService

@bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite_user():
    """Invite a new user to the team"""
    # Check permissions - only Admins and project owners can invite
    if not current_user.has_role('Admin'):
        owned_projects = Project.query.filter_by(owner_id=current_user.id).all()
        if not owned_projects:
            flash('You do not have permission to invite users.', 'danger')
            return redirect(url_for('team.dashboard'))

    if request.method == 'POST':
        email = sanitize_input(request.form.get('email', '').strip().lower())
        role_id = request.form.get('role_id', type=int)
        project_id = request.form.get('project_id', type=int) if request.form.get('project_id') else None
        can_edit = bool(request.form.get('can_edit'))
        can_execute = bool(request.form.get('can_execute', True))

        # Validate CSRF token
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token, session.get('csrf_token')):
            flash('Security token expired. Please try again.', 'danger')
            return render_template('invite_user.html', title='Invite User')

        # Validate input
        if not email or not role_id:
            flash('Email and role are required.', 'danger')
            return render_template('invite_user.html', title='Invite User',
                                 email=email, role_id=role_id, project_id=project_id)

        if not validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('invite_user.html', title='Invite User',
                                 email=email, role_id=role_id, project_id=project_id)

        # Get role
        role = Role.query.get(role_id)
        if not role:
            flash('Invalid role selected.', 'danger')
            return render_template('invite_user.html', title='Invite User',
                                 email=email, project_id=project_id)

        # Validate project if specified
        project = None
        if project_id:
            project = Project.query.get(project_id)
            if not project:
                flash('Invalid project selected.', 'danger')
                return render_template('invite_user.html', title='Invite User',
                                     email=email, role_id=role_id)

            # Check permission to invite to this project
            if not current_user.can_edit_project(project):
                flash('You do not have permission to invite users to this project.', 'danger')
                return render_template('invite_user.html', title='Invite User',
                                     email=email, role_id=role_id)

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            if project:
                # Check if already a member of the project
                existing_member = ProjectMember.query.filter_by(
                    project_id=project.id,
                    user_id=existing_user.id
                ).first()

                if existing_member:
                    flash('This user is already a member of the selected project.', 'info')
                    return render_template('invite_user.html', title='Invite User')
                else:
                    # Add user to project directly
                    member = ProjectMember(
                        project_id=project.id,
                        user_id=existing_user.id,
                        can_edit=can_edit,
                        can_execute=can_execute
                    )
                    db.session.add(member)
                    db.session.commit()

                    flash(f'User {email} has been added to the project {project.name}.', 'success')
                    return redirect(url_for('team.dashboard'))
            else:
                flash('This user already exists in the system.', 'info')
                return render_template('invite_user.html', title='Invite User',
                                     email='', role_id=role_id, project_id=project_id)

        # Check for existing pending invitation
        existing_invitation = InvitationToken.query.filter(
            InvitationToken.email == email,
            InvitationToken.project_id == project_id,
            InvitationToken.used_at.is_(None),
            InvitationToken.expires_at > datetime.now(timezone.utc)
        ).first()

        if existing_invitation:
            flash('A pending invitation already exists for this email and project.', 'info')
            return render_template('invite_user.html', title='Invite User',
                                 email='', role_id=role_id, project_id=project_id)

        # Create invitation token
        try:
            token = generate_invitation_token()
            expires_at = datetime.now(timezone.utc) + timedelta(hours=72)  # 3 days

            invitation = InvitationToken(
                email=email,
                token=token,
                project_id=project_id,
                role_id=role_id,
                can_edit=can_edit,
                can_execute=can_execute,
                created_by_id=current_user.id,
                expires_at=expires_at
            )

            db.session.add(invitation)
            db.session.commit()

            # Send invitation email
            email_result = EmailService.send_invitation_email(invitation, current_user)

            if email_result['success']:
                flash(f'Invitation sent successfully to {email}.', 'success')
            else:
                flash(f'Invitation created but email could not be sent: {email_result["error"]}', 'warning')

            return redirect(url_for('team.dashboard'))

        except Exception as e:
            db.session.rollback()
            flash('Failed to create invitation. Please try again.', 'danger')
            return render_template('invite_user.html', title='Invite User',
                                 email=email, role_id=role_id, project_id=project_id)

    # GET request - show invitation form
    # Get projects user can invite to
    if current_user.has_role('Admin'):
        projects = Project.query.order_by(Project.name).all()
    else:
        projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.name).all()

    roles = Role.query.order_by(Role.name).all()

    # Generate CSRF token
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token

    return render_template('invite_user.html',
                         title='Invite User',
                         projects=projects,
                         roles=roles,
                         csrf_token=csrf_token)

@bp.route('/users')
@login_required
@role_required('Admin')
def list_users():
    """List all users (Admin only)"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()
    status_filter = request.args.get('status', '').strip()

    # Build query
    query = User.query

    if search:
        query = query.filter(
            db.or_(
                User.username.contains(search),
                User.email.contains(search)
            )
        )

    if role_filter:
        query = query.join(Role).filter(Role.name == role_filter)

    if status_filter == 'active':
        query = query.filter(User.is_active == True)
    elif status_filter == 'inactive':
        query = query.filter(User.is_active == False)

    # Order and paginate
    users = query.order_by(User.username).paginate(
        page=page,
        per_page=20,
        error_out=False
    )

    roles = Role.query.order_by(Role.name).all()

    return render_template('user_list.html',
                         title='User Management',
                         users=users,
                         roles=roles,
                         current_search=search,
                         current_role=role_filter,
                         current_status=status_filter)

@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('Admin')
def edit_user(user_id):
    """Edit user details (Admin only)"""
    user = User.query.get_or_404(user_id)

    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', '').strip())
        email = sanitize_input(request.form.get('email', '').strip().lower())
        role_id = request.form.get('role_id', type=int)
        is_active = bool(request.form.get('is_active'))

        # Validate CSRF token
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token, session.get('csrf_token')):
            flash('Security token expired. Please try again.', 'danger')
            return redirect(url_for('team.edit_user', user_id=user_id))

        # Validate input
        if not username or not email or not role_id:
            flash('All fields are required.', 'danger')
            return render_template('edit_user.html', title='Edit User', user=user)

        # Check for duplicates
        if username != user.username:
            if User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
                return render_template('edit_user.html', title='Edit User', user=user)

        if email != user.email:
            if User.query.filter_by(email=email).first():
                flash('Email address already exists.', 'danger')
                return render_template('edit_user.html', title='Edit User', user=user)

        # Get role
        role = Role.query.get(role_id)
        if not role:
            flash('Invalid role selected.', 'danger')
            return render_template('edit_user.html', title='Edit User', user=user)

        # Update user
        try:
            user.username = username
            user.email = email
            user.role = role
            user.is_active = is_active

            db.session.commit()

            flash(f'User {username} updated successfully.', 'success')
            return redirect(url_for('team.list_users'))

        except Exception as e:
            db.session.rollback()
            flash('Failed to update user. Please try again.', 'danger')

    roles = Role.query.order_by(Role.name).all()

    # Generate CSRF token
    csrf_token = generate_csrf_token()
    session['csrf_token'] = csrf_token

    return render_template('edit_user.html',
                         title='Edit User',
                         user=user,
                         roles=roles,
                         csrf_token=csrf_token)

@bp.route('/invitations')
@login_required
def list_invitations():
    """List pending invitations"""
    if current_user.has_role('Admin'):
        invitations = InvitationToken.query.filter(
            InvitationToken.used_at.is_(None)
        ).order_by(InvitationToken.created_at.desc()).all()
    else:
        invitations = InvitationToken.query.filter(
            InvitationToken.created_by_id == current_user.id,
            InvitationToken.used_at.is_(None)
        ).order_by(InvitationToken.created_at.desc()).all()

    return render_template('invitation_list.html',
                         title='Pending Invitations',
                         invitations=invitations)

@bp.route('/invitations/<int:invitation_id>/resend', methods=['POST'])
@login_required
def resend_invitation(invitation_id):
    """Resend an invitation email"""
    invitation = InvitationToken.query.get_or_404(invitation_id)

    # Check permission
    if not current_user.has_role('Admin') and invitation.created_by_id != current_user.id:
        flash('You do not have permission to resend this invitation.', 'danger')
        return redirect(url_for('team.list_invitations'))

    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        flash('Security token expired. Please try again.', 'danger')
        return redirect(url_for('team.list_invitations'))

    if invitation.is_used:
        flash('This invitation has already been used.', 'info')
        return redirect(url_for('team.list_invitations'))

    if invitation.is_expired:
        flash('This invitation has expired and cannot be resent.', 'warning')
        return redirect(url_for('team.list_invitations'))

    # Resend email
    email_result = EmailService.send_invitation_email(invitation, current_user)

    if email_result['success']:
        flash(f'Invitation resent successfully to {invitation.email}.', 'success')
    else:
        flash(f'Failed to resend invitation: {email_result["error"]}', 'danger')

    return redirect(url_for('team.list_invitations'))

@bp.route('/invitations/<int:invitation_id>/cancel', methods=['POST'])
@login_required
def cancel_invitation(invitation_id):
    """Cancel a pending invitation"""
    invitation = InvitationToken.query.get_or_404(invitation_id)

    # Check permission
    if not current_user.has_role('Admin') and invitation.created_by_id != current_user.id:
        flash('You do not have permission to cancel this invitation.', 'danger')
        return redirect(url_for('team.list_invitations'))

    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        flash('Security token expired. Please try again.', 'danger')
        return redirect(url_for('team.list_invitations'))

    if invitation.is_used:
        flash('This invitation has already been used and cannot be cancelled.', 'info')
        return redirect(url_for('team.list_invitations'))

    try:
        email = invitation.email
        db.session.delete(invitation)
        db.session.commit()

        flash(f'Invitation to {email} has been cancelled.', 'success')

    except Exception as e:
        db.session.rollback()
        flash('Failed to cancel invitation. Please try again.', 'danger')

    return redirect(url_for('team.list_invitations'))

@bp.route('/project/<int:project_id>/members')
@login_required
@project_access_required()
def project_members(project_id):
    """Manage project team members"""
    project = Project.query.get_or_404(project_id)

    # Get project members
    members = db.session.query(ProjectMember, User).join(
        User, ProjectMember.user_id == User.id
    ).filter(ProjectMember.project_id == project.id).all()

    # Check if user can edit project members
    can_edit = current_user.can_edit_project(project)

    return render_template('project_members.html',
                         title=f'Team: {project.name}',
                         project=project,
                         members=members,
                         can_edit=can_edit)

@bp.route('/project/<int:project_id>/members/<int:member_id>/edit', methods=['POST'])
@login_required
@project_access_required(edit_required=True)
def edit_project_member(project_id, member_id):
    """Edit project member permissions"""
    project = Project.query.get_or_404(project_id)
    member = ProjectMember.query.filter_by(
        id=member_id,
        project_id=project.id
    ).first_or_404()

    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})

    can_edit = bool(request.form.get('can_edit'))
    can_execute = bool(request.form.get('can_execute'))

    try:
        member.can_edit = can_edit
        member.can_execute = can_execute
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Member permissions updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to update permissions'})

@bp.route('/project/<int:project_id>/members/<int:member_id>/remove', methods=['POST'])
@login_required
@project_access_required(edit_required=True)
def remove_project_member(project_id, member_id):
    """Remove a member from the project"""
    project = Project.query.get_or_404(project_id)
    member = ProjectMember.query.filter_by(
        id=member_id,
        project_id=project.id
    ).first_or_404()

    # Validate CSRF token
    csrf_token = request.form.get('csrf_token')
    if not validate_csrf_token(csrf_token, session.get('csrf_token')):
        return jsonify({'success': False, 'error': 'Security token expired'})

    # Don't allow removing the project owner
    if member.user_id == project.owner_id:
        return jsonify({'success': False, 'error': 'Cannot remove the project owner'})

    try:
        username = member.user.username
        db.session.delete(member)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'{username} has been removed from the project'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Failed to remove member'})

# Add CSRF token to session for AJAX requests
@bp.before_request
def inject_csrf_token():
    """Inject CSRF token into session for AJAX requests"""
    if 'csrf_token' not in session:
        session['csrf_token'] = generate_csrf_token()