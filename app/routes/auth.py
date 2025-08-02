from flask import Blueprint, render_template, redirect, url_for, flash, request, session  # add session if needed elsewhere
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Email
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlparse, urljoin
from datetime import datetime, timedelta, timezone
import secrets

from app import db
from app.models import User, Role, InvitationToken
from app.utils.security import (
    validate_email, validate_username, validate_password_strength,
    sanitize_input, generate_csrf_token, validate_csrf_token,
    generate_invitation_token
)
from app.emailer import EmailService

bp = Blueprint('auth', __name__)

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign In')

def is_safe_url(target):
    """Check if a redirect URL is safe"""
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc

@bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    form = LoginForm()
    
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if form.validate_on_submit():
        email = sanitize_input(form.email.data.strip().lower())
        password = form.password.data
        remember_me = form.remember_me.data
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            if not user.is_active:
                flash('Your account has been deactivated. Please contact an administrator.', 'warning')
                return render_template('login.html', title='Sign In', form=form)
            
            # Update last login
            user.last_login = datetime.now(timezone.utc)
            db.session.commit()
            
            # Log the user in
            login_user(user, remember=remember_me)
            
            # Handle redirect
            next_page = request.args.get('next')
            if not next_page or not is_safe_url(next_page):
                next_page = url_for('main.dashboard')
            
            flash(f'Welcome back to TestCraft Pro, {user.username}!', 'success')
            return redirect(next_page)
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html', title='Sign In', form=form)

@bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', '').strip())
        email = sanitize_input(request.form.get('email', '').strip().lower())
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate CSRF token
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token, session.get('csrf_token')):
            flash('Security token expired. Please try again.', 'danger')
            return render_template('register.html', title='Sign Up')
        
        # Validate input
        if not all([username, email, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email=email)
        
        # Validate username
        username_validation = validate_username(username)
        if not username_validation:
            flash('Username must be 3-30 characters and contain only letters, numbers, dashes, and underscores.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email=email)
        
        # Validate email
        if not validate_email(email):
            flash('Please enter a valid email address.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email=email)
        
        # Validate password
        password_validation = validate_password_strength(password)
        if not password_validation['valid']:
            flash(password_validation['message'], 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email=email)
        
        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email=email)
        
        # Check for existing users
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username='', email=email)
        
        if User.query.filter_by(email=email).first():
            flash('Email address already registered. Please use a different email or try logging in.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email='')
        
        # Create new user
        try:
            # Get default role (Tester)
            default_role = Role.query.filter_by(name='Tester').first()
            if not default_role:
                default_role = Role(name='Tester', description='Can create, edit, and execute tests')
                db.session.add(default_role)
                db.session.flush()
            
            user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash(password),
                role=default_role,
                is_active=True
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Welcome to TestCraft Pro! Your account has been created successfully. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html', title='Sign Up', 
                                 username=username, email=email)
    
    return render_template('register.html', title='Sign Up')

@bp.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    flash(f'You have been logged out from TestCraft Pro. Thank you for using our platform, {username}!', 'info')
    return redirect(url_for('auth.login'))

@bp.route('/accept-invite')
def accept_invite():
    """Accept team invitation"""
    token = request.args.get('token')
    
    if not token:
        flash('Invalid invitation link.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Find invitation token
    invitation = InvitationToken.query.filter_by(token=token).first()
    
    if not invitation:
        flash('Invalid or expired invitation link.', 'danger')
        return redirect(url_for('auth.login'))
    
    if invitation.is_expired:
        flash('This invitation has expired.', 'warning')
        return redirect(url_for('auth.login'))
    
    if invitation.is_used:
        flash('This invitation has already been used.', 'info')
        return redirect(url_for('auth.login'))
    
    # Check if user already exists
    existing_user = User.query.filter_by(email=invitation.email).first()
    
    if existing_user:
        # User exists, just add them to the project/role
        if invitation.project_id:
            from app.models import ProjectMember
            
            # Check if already a member
            existing_member = ProjectMember.query.filter_by(
                project_id=invitation.project_id,
                user_id=existing_user.id
            ).first()
            
            if not existing_member:
                member = ProjectMember(
                    project_id=invitation.project_id,
                    user_id=existing_user.id,
                    can_edit=invitation.can_edit,
                    can_execute=invitation.can_execute
                )
                db.session.add(member)
        
        # Update role if it's higher privilege
        if invitation.role.name == 'Admin' or (invitation.role.name == 'Tester' and existing_user.role.name == 'Viewer'):
            existing_user.role = invitation.role
        
        # Mark invitation as used
        invitation.used_at = datetime.now(timezone.utc)
        db.session.commit()
        
        flash('You have been added to the team! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    # Store invitation data in session for registration
    session['invitation_data'] = {
        'token': token,
        'email': invitation.email,
        'role_id': invitation.role_id,
        'project_id': invitation.project_id,
        'can_edit': invitation.can_edit,
        'can_execute': invitation.can_execute
    }
    
    return redirect(url_for('auth.register_from_invite'))

@bp.route('/register-invite', methods=['GET', 'POST'])
def register_from_invite():
    """Register from team invitation"""
    invitation_data = session.get('invitation_data')
    
    if not invitation_data:
        flash('Invalid invitation session. Please use the invitation link again.', 'danger')
        return redirect(url_for('auth.login'))
    
    # Verify invitation is still valid
    invitation = InvitationToken.query.filter_by(token=invitation_data['token']).first()
    
    if not invitation or invitation.is_expired or invitation.is_used:
        session.pop('invitation_data', None)
        flash('Invalid or expired invitation.', 'danger')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        username = sanitize_input(request.form.get('username', '').strip())
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validate CSRF token
        csrf_token = request.form.get('csrf_token')
        if not validate_csrf_token(csrf_token, session.get('csrf_token')):
            flash('Security token expired. Please try again.', 'danger')
            return render_template('register.html', title='Complete Registration',
                                 email=invitation_data['email'], is_invite=True)
        
        # Validate input
        if not all([username, password, confirm_password]):
            flash('All fields are required.', 'danger')
            return render_template('register.html', title='Complete Registration',
                                 username=username, email=invitation_data['email'], is_invite=True)
        
        # Validate username
        if not validate_username(username):
            flash('Username must be 3-30 characters and contain only letters, numbers, dashes, and underscores.', 'danger')
            return render_template('register.html', title='Complete Registration',
                                 username=username, email=invitation_data['email'], is_invite=True)
        
        # Validate password
        password_validation = validate_password_strength(password)
        if not password_validation['valid']:
            flash(password_validation['message'], 'danger')
            return render_template('register.html', title='Complete Registration',
                                 username=username, email=invitation_data['email'], is_invite=True)
        
        # Check password confirmation
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html', title='Complete Registration',
                                 username=username, email=invitation_data['email'], is_invite=True)
        
        # Check for existing username
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return render_template('register.html', title='Complete Registration',
                                 username='', email=invitation_data['email'], is_invite=True)
        
        # Create user
        try:
            role = Role.query.get(invitation_data['role_id'])
            
            user = User(
                username=username,
                email=invitation_data['email'],
                password_hash=generate_password_hash(password),
                role=role,
                is_active=True
            )
            
            db.session.add(user)
            db.session.flush()  # Get user ID
            
            # Add to project if specified
            if invitation_data['project_id']:
                from app.models import ProjectMember
                member = ProjectMember(
                    project_id=invitation_data['project_id'],
                    user_id=user.id,
                    can_edit=invitation_data['can_edit'],
                    can_execute=invitation_data['can_execute']
                )
                db.session.add(member)
            
            # Mark invitation as used
            invitation.used_at = datetime.now(timezone.utc)
            
            db.session.commit()
            
            # Clear session data
            session.pop('invitation_data', None)
            
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'danger')
            return render_template('register.html', title='Complete Registration',
                                 username=username, email=invitation_data['email'], is_invite=True)
    
    return render_template('register.html', 
                         title='Complete Registration',
                         email=invitation_data['email'],
                         is_invite=True)

@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile management"""
    form = LoginForm()  # Ideally replace this with a dedicated ProfileForm

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            username = sanitize_input(request.form.get('username', '').strip())
            email = sanitize_input(request.form.get('email', '').strip().lower())

            if not username or not email:
                flash('Username and email are required.', 'danger')
            elif not validate_username(username):
                flash('Invalid username format.', 'danger')
            elif not validate_email(email):
                flash('Invalid email format.', 'danger')
            elif username != current_user.username and User.query.filter_by(username=username).first():
                flash('Username already exists.', 'danger')
            elif email != current_user.email and User.query.filter_by(email=email).first():
                flash('Email already registered.', 'danger')
            else:
                current_user.username = username
                current_user.email = email
                db.session.commit()
                flash('Profile updated successfully.', 'success')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not all([current_password, new_password, confirm_password]):
                flash('All password fields are required.', 'danger')
            elif not check_password_hash(current_user.password_hash, current_password):
                flash('Current password is incorrect.', 'danger')
            else:
                password_validation = validate_password_strength(new_password)
                if not password_validation['valid']:
                    flash(password_validation['message'], 'danger')
                elif new_password != confirm_password:
                    flash('New passwords do not match.', 'danger')
                else:
                    current_user.password_hash = generate_password_hash(new_password)
                    db.session.commit()
                    flash('Password changed successfully.', 'success')

        return redirect(url_for('auth.profile'))

  

    # On GET
    return render_template('profile.html', title='Profile', form=form)
