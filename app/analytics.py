from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc, and_, case
from app import db
from app.models import ExecutionResult, TestScript, Project, ExecutionStatus

def get_execution_trends(days=30, project_id=None):
    """Get execution trends over specified days"""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = db.session.query(
        func.date(ExecutionResult.started_at).label('date'),
        func.count(ExecutionResult.id).label('total_executions'),
        func.sum(case((ExecutionResult.status == ExecutionStatus.PASSED, 1), else_=0)).label('passed'),
        func.sum(case((ExecutionResult.status == ExecutionStatus.FAILED, 1), else_=0)).label('failed')
    ).filter(ExecutionResult.started_at >= start_date)

    if project_id:
        query = query.filter(ExecutionResult.project_id == project_id)

    results = query.group_by(func.date(ExecutionResult.started_at)).order_by('date').all()

    return [{
        'date': result.date.strftime('%Y-%m-%d'),
        'total': result.total_executions,
        'passed': result.passed or 0,
        'failed': result.failed or 0,
        'pass_rate': round((result.passed or 0) / result.total_executions * 100, 1) if result.total_executions > 0 else 0
    } for result in results]

def get_project_analytics(project_id=None):
    """Get analytics for projects"""
    if project_id:
        projects = [Project.query.get(project_id)]
    else:
        projects = Project.query.all()

    analytics = []
    for project in projects:
        total_executions = ExecutionResult.query.filter_by(project_id=project.id).count()
        passed_executions = ExecutionResult.query.filter_by(
            project_id=project.id, 
            status=ExecutionStatus.PASSED
        ).count()

        analytics.append({
            'project': project,
            'total_executions': total_executions,
            'passed_executions': passed_executions,
            'pass_rate': round(passed_executions / total_executions * 100, 1) if total_executions > 0 else 0,
            'script_count': len(project.test_scripts)
        })

    return analytics

def get_recent_executions(limit=10, project_id=None):
    """Get recent execution results"""
    query = ExecutionResult.query

    if project_id:
        query = query.filter_by(project_id=project_id)

    return query.order_by(ExecutionResult.started_at.desc()).limit(limit).all()

def get_top_failing_scripts(limit=10, project_id=None):
    """Get scripts with highest failure rates"""
    query = db.session.query(
        TestScript,
        func.count(ExecutionResult.id).label('total_runs'),
        func.sum(case((ExecutionResult.status == ExecutionStatus.FAILED, 1), else_=0)).label('failures')
    ).join(ExecutionResult).group_by(TestScript.id)

    if project_id:
        query = query.filter(TestScript.project_id == project_id)

    results = query.having(func.count(ExecutionResult.id) > 0).order_by(desc('failures')).limit(limit).all()

    return [{
        'script': result[0],
        'total_runs': result[1],
        'failures': result[2],
        'failure_rate': round(result[2] / result[1] * 100, 1) if result[1] > 0 else 0
    } for result in results]