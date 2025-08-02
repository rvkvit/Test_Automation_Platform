from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db
import enum
import os

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
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    base_url = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    test_scripts = db.relationship('TestScript', backref='project', lazy=True, cascade='all, delete-orphan')
    members = db.relationship('ProjectMember', backref='project', lazy=True, cascade='all, delete-orphan')
    execution_results = db.relationship('ExecutionResult', backref='project', lazy=True)

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

class TestScript(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    tags = db.Column(db.String(255))  # Comma-separated tags

    # File paths
    playwright_script_path = db.Column(db.String(512))
    robot_script_path = db.Column(db.String(512))

    # Metadata
    browser_type = db.Column(db.String(20))  # chromium, firefox, webkit
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Conversion status
    conversion_status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    conversion_error = db.Column(db.Text)

    # Relationships
    created_by = db.relationship('User', backref='created_scripts')
    execution_results = db.relationship('ExecutionResult', backref='test_script', lazy=True)
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
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"

class ExecutionResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    script_id = db.Column(db.Integer, db.ForeignKey('test_script.id'), nullable=True)  # Null for suite runs

    # Execution metadata
    status = db.Column(db.Enum(ExecutionStatus), default=ExecutionStatus.PENDING)
    started_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = db.Column(db.DateTime)
    duration_seconds = db.Column(db.Float)

    # Results data
    tests_passed = db.Column(db.Integer, default=0)
    tests_failed = db.Column(db.Integer, default=0)
    tests_total = db.Column(db.Integer, default=0)

    # File paths
    log_path = db.Column(db.String(512))
    report_path = db.Column(db.String(512))
    output_xml_path = db.Column(db.String(512))
    video_path = db.Column(db.String(512))

    # Error information
    error_message = db.Column(db.Text)

    # Execution context
    executed_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_suite_run = db.Column(db.Boolean, default=False)
    headless = db.Column(db.Boolean, default=True)

    executed_by = db.relationship('User')

    @property
    def pass_rate(self):
        if self.tests_total == 0:
            return 0
        return (self.tests_passed / self.tests_total) * 100

    def __repr__(self):
        script_name = self.test_script.name if self.test_script else 'Suite'
        return f'<ExecutionResult {script_name} - {self.status.value}>'

class InvitationToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=True)  # Null for global invites
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    can_edit = db.Column(db.Boolean, default=False)
    can_execute = db.Column(db.Boolean, default=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)

    project = db.relationship('Project')
    role = db.relationship('Role')
    created_by = db.relationship('User')

    @property
    def is_expired(self):
        return datetime.now(timezone.utc) > self.expires_at.replace(tzinfo=timezone.utc)

    @property
    def is_used(self):
        return self.used_at is not None

    def __repr__(self):
        return f'<InvitationToken {self.email}>'

# Initialize default roles
def create_default_roles():
    roles_data = [
        ('Admin', 'Full system access including user management'),
        ('Tester', 'Can create, edit, and execute tests'),
        ('Viewer', 'Read-only access to test results and analytics')
    ]

    for name, description in roles_data:
        if not Role.query.filter_by(name=name).first():
            role = Role(name=name, description=description)
            db.session.add(role)

    db.session.commit()