from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('integrations', __name__, url_prefix='/integrations')

@bp.route('/')
@login_required
def index():
    return render_template('integrations.html')
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user

bp = Blueprint('integrations', __name__)

@bp.route('/')
@login_required
def index():
    """Integrations dashboard"""
    return render_template('integrations.html', title='Integrations')

@bp.route('/configure/<integration_type>')
@login_required
def configure(integration_type):
    """Configure specific integration"""
    return render_template('integrations.html', 
                         title=f'Configure {integration_type.title()}',
                         integration_type=integration_type)
