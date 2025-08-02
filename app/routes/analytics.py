from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, and_
from app import db
from app.models import Project, ExecutionResult, TestScript, ExecutionStatus

bp = Blueprint('analytics', __name__)

@bp.route('/')
@bp.route('/dashboard')
@login_required
def dashboard():
    """Analytics dashboard"""
    days = int(request.args.get('days', 7))
    project_id = request.args.get('project_id')

    # Date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    # Get analytics data
    analytics_data = get_analytics_data(project_id, start_date, end_date, days)

    # Get projects for filter
    if current_user.has_role('Admin'):
        projects = Project.query.order_by(Project.name).all()
    else:
        projects = Project.query.filter_by(owner_id=current_user.id).order_by(Project.name).all()

    current_project = None
    if project_id:
        current_project = Project.query.get(project_id)

    return render_template('analytics.html',
                         title='Analytics',
                         analytics_data=analytics_data,
                         projects=projects,
                         current_project=current_project,
                         days=days)

@bp.route('/api/trends')
@login_required
def api_trends():
    """API endpoint for trend data"""
    days = int(request.args.get('days', 7))
    project_id = request.args.get('project_id')

    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)

    trends = get_trend_data(project_id, start_date, end_date)

    return jsonify({
        'success': True,
        'trends': trends
    })

def get_analytics_data(project_id, start_date, end_date, days):
    """Get analytics data for the dashboard"""
    base_query = ExecutionResult.query.filter(
        ExecutionResult.started_at >= start_date,
        ExecutionResult.started_at <= end_date
    )

    if project_id:
        base_query = base_query.filter(ExecutionResult.project_id == project_id)
    elif not current_user.has_role('Admin'):
        # Filter to user's projects only
        user_projects = Project.query.filter_by(owner_id=current_user.id).all()
        project_ids = [p.id for p in user_projects]
        if project_ids:
            base_query = base_query.filter(ExecutionResult.project_id.in_(project_ids))
        else:
            base_query = base_query.filter(False)  # No results

    # Get trend data
    trends = get_trend_data(project_id, start_date, end_date)

    # Summary metrics
    total_executions = base_query.count()
    passed_executions = base_query.filter(ExecutionResult.status == ExecutionStatus.PASSED).count()
    failed_executions = base_query.filter(ExecutionResult.status == ExecutionStatus.FAILED).count()

    pass_rate = (passed_executions / total_executions * 100) if total_executions > 0 else 0

    return {
        'trends': trends,
        'total_executions': total_executions,
        'passed_executions': passed_executions,
        'failed_executions': failed_executions,
        'pass_rate': round(pass_rate, 1),
        'summary': {
            'total_executions': total_executions,
            'pass_rate_7_days': round(pass_rate, 1),
            'total_projects': Project.query.count() if current_user.has_role('Admin') else Project.query.filter_by(owner_id=current_user.id).count(),
            'total_scripts': TestScript.query.count() if current_user.has_role('Admin') else db.session.query(TestScript).join(Project).filter(Project.owner_id == current_user.id).count()
        }
    }

def get_trend_data(project_id, start_date, end_date):
    """Get daily trend data"""
    base_query = db.session.query(
        func.date(ExecutionResult.started_at).label('date'),
        func.count(ExecutionResult.id).label('total'),
        func.sum(func.case([(ExecutionResult.status == ExecutionStatus.PASSED, 1)], else_=0)).label('passed'),
        func.sum(func.case([(ExecutionResult.status == ExecutionStatus.FAILED, 1)], else_=0)).label('failed')
    ).filter(
        ExecutionResult.started_at >= start_date,
        ExecutionResult.started_at <= end_date
    )

    if project_id:
        base_query = base_query.filter(ExecutionResult.project_id == project_id)
    elif not current_user.has_role('Admin'):
        user_projects = Project.query.filter_by(owner_id=current_user.id).all()
        project_ids = [p.id for p in user_projects]
        if project_ids:
            base_query = base_query.filter(ExecutionResult.project_id.in_(project_ids))
        else:
            return []

    results = base_query.group_by(func.date(ExecutionResult.started_at)).all()

    trends = []
    for result in results:
        total = result.total or 0
        passed = result.passed or 0
        failed = result.failed or 0
        pass_rate = (passed / total * 100) if total > 0 else 0

        trends.append({
            'date': result.date.isoformat(),
            'total': total,
            'passed': passed,
            'failed': failed,
            'pass_rate': round(pass_rate, 1)
        })

    return trends