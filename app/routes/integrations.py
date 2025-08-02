from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint('integrations', __name__, url_prefix='/integrations')

@bp.route('/')
@login_required
def index():
    return render_template('integrations.html')
