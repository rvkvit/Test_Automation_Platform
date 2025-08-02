from flask import Blueprint, render_template, request, jsonify, make_response
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import csv
import io

from app.models import Project, ProjectMember
from app.analytics import AnalyticsService
from app.auth import project_access_required

bp = Blueprint('analytics', __name__)

@bp.route('/')
@login_required
def dashboard():
    """Analytics dashboard with global or project-specific view"""
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    # Get accessible projects for filter
    accessible_projects = get_accessible_projects()
    
    if project_id:
        # Project-specific analytics
        project = Project.query.get(project_id)
        
        if not project or not current_user.can_access_project(project):
            project_id = None
            project = None
        
        if project:
            analytics_data = AnalyticsService.get_project_analytics(project_id, days)
        else:
            analytics_data = AnalyticsService.get_global_analytics(days)
    else:
        # Global analytics
        analytics_data = AnalyticsService.get_global_analytics(days)
        project = None
    
    return render_template('analytics.html',
                         title='Analytics Dashboard',
                         analytics_data=analytics_data,
                         accessible_projects=accessible_projects,
                         current_project=project,
                         current_project_id=project_id,
                         current_days=days)

@bp.route('/api/trends')
@login_required
def api_trends():
    """API endpoint for trend data (for charts)"""
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    try:
        if project_id:
            # Check project access
            project = Project.query.get(project_id)
            if not project or not current_user.can_access_project(project):
                return jsonify({'error': 'Access denied'}), 403
            
            analytics_data = AnalyticsService.get_project_analytics(project_id, days)
        else:
            analytics_data = AnalyticsService.get_global_analytics(days)
        
        # Format data for Chart.js
        trend_data = analytics_data['trends']
        
        chart_data = {
            'labels': [item['date'] for item in trend_data],
            'datasets': [
                {
                    'label': 'Passed Tests',
                    'data': [item['passed'] for item in trend_data],
                    'backgroundColor': 'rgba(40, 167, 69, 0.2)',
                    'borderColor': 'rgba(40, 167, 69, 1)',
                    'borderWidth': 2,
                    'tension': 0.1
                },
                {
                    'label': 'Failed Tests',
                    'data': [item['failed'] for item in trend_data],
                    'backgroundColor': 'rgba(220, 53, 69, 0.2)',
                    'borderColor': 'rgba(220, 53, 69, 1)',
                    'borderWidth': 2,
                    'tension': 0.1
                },
                {
                    'label': 'Pass Rate (%)',
                    'data': [item['pass_rate'] for item in trend_data],
                    'backgroundColor': 'rgba(0, 123, 255, 0.2)',
                    'borderColor': 'rgba(0, 123, 255, 1)',
                    'borderWidth': 2,
                    'tension': 0.1,
                    'yAxisID': 'y1'
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/duration-trends')
@login_required
def api_duration_trends():
    """API endpoint for duration trend data"""
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    try:
        if project_id:
            # Check project access
            project = Project.query.get(project_id)
            if not project or not current_user.can_access_project(project):
                return jsonify({'error': 'Access denied'}), 403
            
            analytics_data = AnalyticsService.get_project_analytics(project_id, days)
        else:
            analytics_data = AnalyticsService.get_global_analytics(days)
        
        # Format duration data for Chart.js
        if 'duration_trends' in analytics_data:
            duration_data = analytics_data['duration_trends']
        else:
            # Fallback if duration trends not available in global analytics
            duration_data = []
        
        chart_data = {
            'labels': [item['date'] for item in duration_data],
            'datasets': [
                {
                    'label': 'Average Duration (seconds)',
                    'data': [item['avg_duration'] for item in duration_data],
                    'backgroundColor': 'rgba(255, 193, 7, 0.2)',
                    'borderColor': 'rgba(255, 193, 7, 1)',
                    'borderWidth': 2,
                    'tension': 0.1
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'chart_data': chart_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/flakiness')
@login_required
def api_flakiness():
    """API endpoint for flakiness data"""
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    if not project_id:
        return jsonify({'error': 'Project ID required for flakiness analysis'}), 400
    
    try:
        # Check project access
        project = Project.query.get(project_id)
        if not project or not current_user.can_access_project(project):
            return jsonify({'error': 'Access denied'}), 403
        
        analytics_data = AnalyticsService.get_project_analytics(project_id, days)
        flakiness_data = analytics_data.get('flakiness', {})
        
        return jsonify({
            'success': True,
            'flakiness_data': flakiness_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/script-performance')
@login_required
def api_script_performance():
    """API endpoint for script performance data"""
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    if not project_id:
        return jsonify({'error': 'Project ID required for script performance analysis'}), 400
    
    try:
        # Check project access
        project = Project.query.get(project_id)
        if not project or not current_user.can_access_project(project):
            return jsonify({'error': 'Access denied'}), 403
        
        analytics_data = AnalyticsService.get_project_analytics(project_id, days)
        script_performance = analytics_data.get('script_performance', [])
        
        return jsonify({
            'success': True,
            'script_performance': script_performance
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/export')
@login_required
def export_csv():
    """Export analytics data as CSV"""
    project_id = request.args.get('project_id', type=int)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    if project_id:
        # Check project access
        project = Project.query.get(project_id)
        if not project or not current_user.can_access_project(project):
            return jsonify({'error': 'Access denied'}), 403
    
    try:
        # Get CSV data
        csv_data = AnalyticsService.export_analytics_csv(project_id, days)
        
        # Create CSV file in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        for row in csv_data:
            writer.writerow(row)
        
        # Create response
        csv_content = output.getvalue()
        output.close()
        
        response = make_response(csv_content)
        response.headers['Content-Type'] = 'text/csv'
        
        # Generate filename
        if project_id:
            filename = f"analytics_project_{project_id}_{days}days_{datetime.now().strftime('%Y%m%d')}.csv"
        else:
            filename = f"analytics_global_{days}days_{datetime.now().strftime('%Y%m%d')}.csv"
        
        response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/project/<int:project_id>')
@login_required
@project_access_required()
def project_analytics(project_id):
    """Detailed analytics for a specific project"""
    project = Project.query.get_or_404(project_id)
    days = request.args.get('days', 30, type=int)
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    analytics_data = AnalyticsService.get_project_analytics(project_id, days)
    
    return render_template('project_analytics.html',
                         title=f'Analytics: {project.name}',
                         project=project,
                         analytics_data=analytics_data,
                         current_days=days)

@bp.route('/system-metrics')
@login_required
def system_metrics():
    """System-wide metrics (Admin only)"""
    if not current_user.has_role('Admin'):
        return redirect(url_for('analytics.dashboard'))
    
    try:
        # Get comprehensive system metrics
        from app.models import User, ExecutionResult
        from sqlalchemy import func
        
        # User statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        
        # Execution statistics by user
        user_execution_stats = db.session.query(
            User.username,
            func.count(ExecutionResult.id).label('execution_count'),
            func.avg(ExecutionResult.duration_seconds).label('avg_duration')
        ).join(
            ExecutionResult, User.id == ExecutionResult.executed_by_id
        ).group_by(
            User.id, User.username
        ).order_by(
            func.count(ExecutionResult.id).desc()
        ).limit(10).all()
        
        # Recent activity
        recent_executions = ExecutionResult.query.order_by(
            ExecutionResult.started_at.desc()
        ).limit(50).all()
        
        system_data = {
            'total_users': total_users,
            'active_users': active_users,
            'user_execution_stats': [
                {
                    'username': stat.username,
                    'execution_count': stat.execution_count,
                    'avg_duration': round(stat.avg_duration or 0, 2)
                }
                for stat in user_execution_stats
            ],
            'recent_executions': recent_executions
        }
        
        return render_template('system_metrics.html',
                             title='System Metrics',
                             system_data=system_data)
        
    except Exception as e:
        flash(f'Failed to load system metrics: {str(e)}', 'danger')
        return redirect(url_for('analytics.dashboard'))

def get_accessible_projects():
    """Get projects accessible to the current user"""
    if current_user.has_role('Admin'):
        return Project.query.order_by(Project.name).all()
    else:
        # Get owned projects
        owned_projects = Project.query.filter_by(owner_id=current_user.id).all()
        
        # Get member projects
        member_projects = db.session.query(Project).join(
            ProjectMember, Project.id == ProjectMember.project_id
        ).filter(ProjectMember.user_id == current_user.id).all()
        
        # Combine and deduplicate
        project_dict = {p.id: p for p in owned_projects + member_projects}
        projects = list(project_dict.values())
        projects.sort(key=lambda p: p.name)
        
        return projects

@bp.route('/api/dashboard-metrics')
@login_required
def api_dashboard_metrics():
    """API endpoint for dashboard metrics (for real-time updates)"""
    try:
        metrics = AnalyticsService.get_dashboard_metrics()
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/compare-projects')
@login_required
def compare_projects():
    """Compare analytics between multiple projects"""
    project_ids = request.args.getlist('project_ids', type=int)
    days = request.args.get('days', 30, type=int)
    
    if not project_ids or len(project_ids) < 2:
        flash('Please select at least 2 projects to compare.', 'warning')
        return redirect(url_for('analytics.dashboard'))
    
    # Validate days parameter
    if days not in [7, 30, 90, 365]:
        days = 30
    
    # Check access to all selected projects
    accessible_projects = get_accessible_projects()
    accessible_project_ids = [p.id for p in accessible_projects]
    
    valid_project_ids = [pid for pid in project_ids if pid in accessible_project_ids]
    
    if len(valid_project_ids) != len(project_ids):
        flash('Some selected projects are not accessible.', 'warning')
    
    if len(valid_project_ids) < 2:
        flash('At least 2 accessible projects are required for comparison.', 'warning')
        return redirect(url_for('analytics.dashboard'))
    
    # Get analytics data for each project
    comparison_data = []
    
    for project_id in valid_project_ids:
        project = Project.query.get(project_id)
        analytics_data = AnalyticsService.get_project_analytics(project_id, days)
        
        comparison_data.append({
            'project': project,
            'analytics': analytics_data
        })
    
    return render_template('project_comparison.html',
                         title='Project Comparison',
                         comparison_data=comparison_data,
                         current_days=days)
