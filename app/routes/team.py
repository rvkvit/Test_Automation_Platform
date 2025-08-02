from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import User, Project, ProjectMember, Role, InvitationToken
from app.utils.security import generate_secure_token
from app.emailer import send_invitation_email
from datetime import datetime, timedelta, timezone
import secrets

bp = Blueprint('team', __name__)

@bp.route('/')
@login_required
def index():
    """Team management dashboard"""
    if not current_user.has_role('Admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    users = User.query.all()
    roles = Role.query.all()
    pending_invitations = InvitationToken.query.filter_by(used_at=None).all()

    return render_template('team_dashboard.html',
                         title='Team Management',
                         users=users,
                         roles=roles,
                         pending_invitations=pending_invitations)

@bp.route('/invite', methods=['GET', 'POST'])
@login_required
def invite_user():
    """Invite a new user"""
    if not current_user.has_role('Admin'):
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        project_id = request.form.get('project_id') or None
        can_edit = bool(request.form.get('can_edit'))
        can_execute = bool(request.form.get('can_execute'))

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User with this email already exists.', 'error')
            return redirect(url_for('team.invite_user'))

        # Generate invitation token
        token = generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

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
        try:
            send_invitation_email(email, token)
            flash(f'Invitation sent to {email}', 'success')
        except Exception as e:
            flash(f'Failed to send invitation email: {str(e)}', 'error')

        return redirect(url_for('team.index'))

    roles = Role.query.all()
    projects = Project.query.all()

    return render_template('invite.html',
                         title='Invite User',
                         roles=roles,
                         projects=projects)

@bp.route('/user/<int:user_id>/change-role', methods=['POST'])
@login_required
def change_user_role():
    """Change a user's role"""
    if not current_user.has_role('Admin'):
        return jsonify({'error': 'Access denied'}), 403

    user_id = request.form.get('user_id')
    role_id = request.form.get('role_id')

    user = User.query.get_or_404(user_id)
    role = Role.query.get_or_404(role_id)

    user.role_id = role_id
    db.session.commit()

    flash(f'Updated {user.username} role to {role.name}', 'success')
    return redirect(url_for('team.index'))

@bp.route('/user/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status():
    """Toggle user active status"""
    if not current_user.has_role('Admin'):
        return jsonify({'error': 'Access denied'}), 403

    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        return jsonify({'error': 'Cannot deactivate yourself'}), 400

    user.is_active = not user.is_active
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    return jsonify({'message': f'User {status} successfully', 'is_active': user.is_active})

@bp.route('/invitation/<token>/revoke', methods=['POST'])
@login_required
def revoke_invitation():
    """Revoke a pending invitation"""
    if not current_user.has_role('Admin'):
        return jsonify({'error': 'Access denied'}), 403

    invitation = InvitationToken.query.filter_by(token=token).first_or_404()

    if invitation.is_used:
        return jsonify({'error': 'Invitation already used'}), 400

    db.session.delete(invitation)
    db.session.commit()

    flash('Invitation revoked successfully', 'success')
    return redirect(url_for('team.index'))