from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db
import enum
import os
import secrets

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

    # Relationships
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f'<Role {self.name}>'

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = db.Column(db.DateTime)

    # Relationships
    projects = db.relationship('Project', backref='owner', lazy=True)
    project_members = db.relationship('ProjectMember', backref='user', lazy=True)
    executions = db.relationship('ExecutionResult', backref='executed_by', lazy=True)
    created_scripts = db.relationship('TestScript', backref='created_by', lazy=True)
    sent_invitations = db.relationship('InvitationToken', backref='created_by', lazy=True)

    def has_role(self, role_name):
        return self.role and self.role.name == role_name

    def can_access_project(self, project):
        if self.has_role('Admin'):
            return True
        if project.owner_id == self.id:
            return True
        return any(pm.project_id == project.id for pm in self.project_members)

    def can_edit_project(self, project):
        if self.has_role('Admin'):
            return True
        if project.owner_id == self.id:
            return True
        member = next((pm for pm in self.project_members if pm.project_id == project.id), None)
        return member and member.can_edit

    def __repr__(self):
        return f'<User {self.username}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_url = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    scripts = db.relationship('TestScript', backref='project', lazy=True, cascade='all, delete-orphan')
    executions = db.relationship('ExecutionResult', backref='project', lazy=True, cascade='all, delete-orphan')
    members = db.relationship('ProjectMember', backref='project', lazy=True, cascade='all, delete-orphan')
    invitations = db.relationship('InvitationToken', backref='project', lazy=True)

    def __repr__(self):
        return f'<Project {self.name}>'

class ProjectMember(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_execute = db.Column(db.Boolean, default=True)
    added_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint('project_id', 'user_id'),)

    def __repr__(self):
        return f'<ProjectMember {self.user_id} in {self.project_id}>'

class TestScript(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    tags = db.Column(db.String(255))  # Comma-separated tags
    playwright_script_path = db.Column(db.String(255))
    robot_script_path = db.Column(db.String(255))
    browser_type = db.Column(db.String(20))  # chromium, firefox, webkit
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    conversion_status = db.Column(db.String(50), default='pending')
    conversion_logs = db.Column(db.Text)
    conversion_error = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    executions = db.relationship('ExecutionResult', backref='script', lazy=True)
    versions = db.relationship('ScriptVersion', backref='script', lazy=True, cascade='all, delete-orphan')

    def get_tags_list(self):
        return [tag.strip() for tag in (self.tags or '').split(',') if tag.strip()]

    def set_tags_list(self, tags_list):
        self.tags = ', '.join(tags_list) if tags_list else ''

    def __repr__(self):
        return f'<TestScript {self.name}>'

class ScriptVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    script_id = db.Column(db.Integer, db.ForeignKey('test_script.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    robot_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_by = db.relationship('User')

    __table_args__ = (db.UniqueConstraint('script_id', 'version_number'),)

class ExecutionStatus(enum.Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    PASSED = 'passed'
    FAILED = 'failed'
    ERROR = 'error'
    CANCELLED = 'cancelled'

class ExecutionResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    script_id = db.Column(db.Integer, db.ForeignKey('test_script.id'))
    status = db.Column(db.Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)
    tests_total = db.Column(db.Integer, default=0)
    tests_passed = db.Column(db.Integer, default=0)
    tests_failed = db.Column(db.Integer, default=0)
    pass_rate = db.Column(db.Float)
    error_message = db.Column(db.Text)
    log_path = db.Column(db.String(255))
    report_path = db.Column(db.String(255))
    output_xml_path = db.Column(db.String(255))
    video_path = db.Column(db.String(255))
    executed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_suite_run = db.Column(db.Boolean, default=False)
    headless = db.Column(db.Boolean, default=True)

    # Legacy properties for backward compatibility
    @property
    def duration(self):
        return self.duration_seconds

    @property
    def test_count(self):
        return self.tests_total

    @property
    def passed_count(self):
        return self.tests_passed

    @property
    def failed_count(self):
        return self.tests_failed

    @property
    def ended_at(self):
        return self.completed_at

    def __repr__(self):
        return f'<ExecutionResult {self.id}>'

class InvitationToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_execute = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)

    # Relationships
    role = db.relationship('Role', backref='invitations')

    @property
    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self):
        return self.used_at is not None

    def __repr__(self):
        return f'<InvitationToken {self.email}>'

def create_default_roles():
    """Create default roles if they don't exist"""
    roles = [
        {'name': 'Admin', 'description': 'Full system access'},
        {'name': 'Tester', 'description': 'Can create and execute tests'},
        {'name': 'Viewer', 'description': 'Read-only access to assigned projects'}
    ]

    for role_data in roles:
        existing_role = Role.query.filter_by(name=role_data['name']).first()
        if not existing_role:
            role = Role(name=role_data['name'], description=role_data['description'])
            db.session.add(role)

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error creating default roles: {e}")