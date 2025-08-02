from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('integrations', __name__)

@bp.route('/')
@login_required
def index():
    """Integrations page"""
    return render_template('integrations.html',
                         title='Integrations')

@bp.route('/ci-cd')
@login_required
def ci_cd():
    """CI/CD integration settings"""
    return render_template('integrations.html',
                         title='CI/CD Integrations',
                         section='ci-cd')

@bp.route('/notifications')
@login_required
def notifications():
    """Notification integration settings"""
    return render_template('integrations.html',
                         title='Notification Integrations',
                         section='notifications')