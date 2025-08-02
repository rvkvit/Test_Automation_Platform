from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc, and_, case
from app import db
from app.models import ExecutionResult, TestScript, Project, ExecutionStatus

class AnalyticsService:
    
    @staticmethod
    def get_dashboard_metrics():
        """Get high-level metrics for the dashboard"""
        
        # Total counts
        total_projects = Project.query.count()
        total_scripts = TestScript.query.count()
        
        # Recent executions (last 10)
        recent_executions = db.session.query(
            ExecutionResult, TestScript, Project
        ).outerjoin(
            TestScript, ExecutionResult.script_id == TestScript.id
        ).join(
            Project, ExecutionResult.project_id == Project.id
        ).order_by(
            desc(ExecutionResult.started_at)
        ).limit(10).all()
        
        # Pass rate last 7 days
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
        recent_results = ExecutionResult.query.filter(
            ExecutionResult.started_at >= seven_days_ago,
            ExecutionResult.status.in_([ExecutionStatus.PASSED, ExecutionStatus.FAILED])
        ).all()
        
        pass_rate = 0
        if recent_results:
            passed = sum(1 for r in recent_results if r.status == ExecutionStatus.PASSED)
            pass_rate = (passed / len(recent_results)) * 100
        
        return {
            'total_projects': total_projects,
            'total_scripts': total_scripts,
            'recent_executions': [
                {
                    'id': result.id,
                    'project_name': project.name,
                    'script_name': script.name if script else 'Suite Run',
                    'status': result.status.value,
                    'duration': result.duration_seconds,
                    'started_at': result.started_at,
                    'is_suite': result.is_suite_run
                }
                for result, script, project in recent_executions
            ],
            'pass_rate_7_days': round(pass_rate, 1)
        }
    
    @staticmethod
    def get_project_analytics(project_id, days=30):
        """Get analytics for a specific project"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Basic stats
        project = Project.query.get(project_id)
        if not project:
            return None
        
        total_scripts = len(project.test_scripts)
        converted_scripts = sum(1 for s in project.test_scripts if s.conversion_status == 'completed')
        
        # Execution stats
        executions = ExecutionResult.query.filter(
            ExecutionResult.project_id == project_id,
            ExecutionResult.started_at >= cutoff_date
        ).all()
        
        # Pass/fail trends
        trend_data = AnalyticsService._get_trend_data(executions, days)
        
        # Duration trends
        duration_data = AnalyticsService._get_duration_trends(executions, days)
        
        # Flakiness analysis
        flakiness_data = AnalyticsService._get_flakiness_analysis(project_id, days)
        
        # Script performance
        script_stats = AnalyticsService._get_script_performance(project_id, days)
        
        return {
            'project': {
                'id': project.id,
                'name': project.name,
                'total_scripts': total_scripts,
                'converted_scripts': converted_scripts
            },
            'trends': trend_data,
            'duration_trends': duration_data,
            'flakiness': flakiness_data,
            'script_performance': script_stats,
            'total_executions': len(executions),
            'period_days': days
        }
    
    @staticmethod
    def get_global_analytics(days=30):
        """Get system-wide analytics"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # All executions in the period
        executions = ExecutionResult.query.filter(
            ExecutionResult.started_at >= cutoff_date
        ).all()
        
        # Global trends
        trend_data = AnalyticsService._get_trend_data(executions, days)
        
        # Project breakdown
        from sqlalchemy import case
        project_stats = db.session.query(
            Project.id,
            Project.name,
            func.count(ExecutionResult.id).label('execution_count'),
            func.avg(ExecutionResult.duration_seconds).label('avg_duration'),
            func.sum(case((ExecutionResult.status == ExecutionStatus.PASSED, 1), else_=0)).label('passed'),
            func.sum(case((ExecutionResult.status == ExecutionStatus.FAILED, 1), else_=0)).label('failed')
        ).join(
            ExecutionResult, Project.id == ExecutionResult.project_id
        ).filter(
            ExecutionResult.started_at >= cutoff_date
        ).group_by(
            Project.id, Project.name
        ).all()
        
        # Most active scripts
        script_activity = db.session.query(
            TestScript.id,
            TestScript.name,
            Project.name.label('project_name'),
            func.count(ExecutionResult.id).label('execution_count'),
            func.avg(ExecutionResult.duration_seconds).label('avg_duration')
        ).join(
            ExecutionResult, TestScript.id == ExecutionResult.script_id
        ).join(
            Project, TestScript.project_id == Project.id
        ).filter(
            ExecutionResult.started_at >= cutoff_date
        ).group_by(
            TestScript.id, TestScript.name, Project.name
        ).order_by(
            desc('execution_count')
        ).limit(10).all()
        
        return {
            'trends': trend_data,
            'project_breakdown': [
                {
                    'project_id': p.id,
                    'project_name': p.name,
                    'execution_count': p.execution_count,
                    'avg_duration': round(p.avg_duration or 0, 2),
                    'pass_rate': round((p.passed / (p.passed + p.failed)) * 100, 1) if (p.passed + p.failed) > 0 else 0
                }
                for p in project_stats
            ],
            'most_active_scripts': [
                {
                    'script_id': s.id,
                    'script_name': s.name,
                    'project_name': s.project_name,
                    'execution_count': s.execution_count,
                    'avg_duration': round(s.avg_duration or 0, 2)
                }
                for s in script_activity
            ],
            'total_executions': len(executions),
            'period_days': days
        }
    
    @staticmethod
    def _get_trend_data(executions, days):
        """Calculate pass/fail trends over time"""
        # Group executions by date
        daily_stats = {}
        
        for execution in executions:
            date_key = execution.started_at.date()
            if date_key not in daily_stats:
                daily_stats[date_key] = {'passed': 0, 'failed': 0, 'total': 0}
            
            daily_stats[date_key]['total'] += 1
            if execution.status == ExecutionStatus.PASSED:
                daily_stats[date_key]['passed'] += 1
            elif execution.status == ExecutionStatus.FAILED:
                daily_stats[date_key]['failed'] += 1
        
        # Fill in missing dates
        start_date = datetime.now().date() - timedelta(days=days)
        trend_data = []
        
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            stats = daily_stats.get(date, {'passed': 0, 'failed': 0, 'total': 0})
            
            pass_rate = (stats['passed'] / stats['total'] * 100) if stats['total'] > 0 else 0
            
            trend_data.append({
                'date': date.isoformat(),
                'passed': stats['passed'],
                'failed': stats['failed'],
                'total': stats['total'],
                'pass_rate': round(pass_rate, 1)
            })
        
        return trend_data
    
    @staticmethod
    def _get_duration_trends(executions, days):
        """Calculate duration trends over time"""
        # Group by date and calculate average duration
        daily_durations = {}
        
        for execution in executions:
            if execution.duration_seconds is None:
                continue
                
            date_key = execution.started_at.date()
            if date_key not in daily_durations:
                daily_durations[date_key] = []
            
            daily_durations[date_key].append(execution.duration_seconds)
        
        # Calculate daily averages
        start_date = datetime.now().date() - timedelta(days=days)
        duration_data = []
        
        for i in range(days + 1):
            date = start_date + timedelta(days=i)
            durations = daily_durations.get(date, [])
            
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            duration_data.append({
                'date': date.isoformat(),
                'avg_duration': round(avg_duration, 2),
                'execution_count': len(durations)
            })
        
        return duration_data
    
    @staticmethod
    def _get_flakiness_analysis(project_id, days):
        """Analyze test flakiness for a project"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        # Get script execution patterns
        script_results = db.session.query(
            TestScript.id,
            TestScript.name,
            func.count(ExecutionResult.id).label('total_runs'),
            func.sum(case((ExecutionResult.status == ExecutionStatus.PASSED, 1), else_=0)).label('passed_runs'),
            func.sum(case((ExecutionResult.status == ExecutionStatus.FAILED, 1), else_=0)).label('failed_runs')
        ).join(
            ExecutionResult, TestScript.id == ExecutionResult.script_id
        ).filter(
            TestScript.project_id == project_id,
            ExecutionResult.started_at >= cutoff_date
        ).group_by(
            TestScript.id, TestScript.name
        ).having(
            func.count(ExecutionResult.id) >= 3  # Only consider scripts with 3+ runs
        ).all()
        
        flaky_scripts = []
        
        for script in script_results:
            if script.total_runs == 0:
                continue
                
            pass_rate = (script.passed_runs / script.total_runs) * 100
            
            # Consider a script flaky if it has both passes and failures
            # and pass rate is between 20% and 80%
            is_flaky = (script.failed_runs > 0 and script.passed_runs > 0 and 
                       20 <= pass_rate <= 80)
            
            # Calculate flakiness index (0-1, where 1 is most flaky)
            if script.total_runs < 2:
                flakiness_index = 0
            else:
                # Flakiness peaks at 50% pass rate
                flakiness_index = 1 - abs(pass_rate - 50) / 50
            
            flaky_scripts.append({
                'script_id': script.id,
                'script_name': script.name,
                'total_runs': script.total_runs,
                'pass_rate': round(pass_rate, 1),
                'flakiness_index': round(flakiness_index, 3),
                'is_flaky': is_flaky
            })
        
        # Sort by flakiness index
        flaky_scripts.sort(key=lambda x: x['flakiness_index'], reverse=True)
        
        return {
            'scripts': flaky_scripts[:10],  # Top 10 most flaky
            'total_analyzed': len(flaky_scripts),
            'flaky_count': sum(1 for s in flaky_scripts if s['is_flaky'])
        }
    
    @staticmethod
    def _get_script_performance(project_id, days):
        """Get performance stats for scripts in a project"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        script_stats = db.session.query(
            TestScript.id,
            TestScript.name,
            func.count(ExecutionResult.id).label('execution_count'),
            func.avg(ExecutionResult.duration_seconds).label('avg_duration'),
            func.max(ExecutionResult.started_at).label('last_run'),
            func.sum(case((ExecutionResult.status == ExecutionStatus.PASSED, 1), else_=0)).label('passed'),
            func.sum(case((ExecutionResult.status == ExecutionStatus.FAILED, 1), else_=0)).label('failed')
        ).join(
            ExecutionResult, TestScript.id == ExecutionResult.script_id
        ).filter(
            TestScript.project_id == project_id,
            ExecutionResult.started_at >= cutoff_date
        ).group_by(
            TestScript.id, TestScript.name
        ).order_by(
            desc('execution_count')
        ).all()
        
        return [
            {
                'script_id': s.id,
                'script_name': s.name,
                'execution_count': s.execution_count,
                'avg_duration': round(s.avg_duration or 0, 2),
                'last_run': s.last_run.isoformat() if s.last_run else None,
                'pass_rate': round((s.passed / (s.passed + s.failed)) * 100, 1) if (s.passed + s.failed) > 0 else 0,
                'stability_score': AnalyticsService._calculate_stability_score(s.passed, s.failed, s.execution_count)
            }
            for s in script_stats
        ]
    
    @staticmethod
    def _calculate_stability_score(passed, failed, total):
        """Calculate a stability score (0-100) for a script"""
        if total == 0:
            return 0
        
        pass_rate = (passed / total) * 100
        
        # Boost score for higher execution counts (more confidence)
        confidence_multiplier = min(1.0, total / 10)  # Max confidence at 10+ runs
        
        # Penalize for any failures
        stability_penalty = (failed / total) * 20  # Up to 20 point penalty
        
        score = (pass_rate * confidence_multiplier) - stability_penalty
        return max(0, min(100, round(score, 1)))
    
    @staticmethod
    def export_analytics_csv(project_id=None, days=30):
        """Export analytics data as CSV format"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        query = db.session.query(
            ExecutionResult,
            TestScript.name.label('script_name'),
            Project.name.label('project_name')
        ).outerjoin(
            TestScript, ExecutionResult.script_id == TestScript.id
        ).join(
            Project, ExecutionResult.project_id == Project.id
        ).filter(
            ExecutionResult.started_at >= cutoff_date
        )
        
        if project_id:
            query = query.filter(ExecutionResult.project_id == project_id)
        
        results = query.order_by(desc(ExecutionResult.started_at)).all()
        
        # Generate CSV data
        csv_data = []
        csv_data.append([
            'Project', 'Script', 'Status', 'Started At', 'Duration (s)',
            'Tests Passed', 'Tests Failed', 'Tests Total', 'Pass Rate (%)',
            'Is Suite Run', 'Executed By', 'Headless'
        ])
        
        for result, script_name, project_name in results:
            csv_data.append([
                project_name,
                script_name or 'Suite Run',
                result.status.value,
                result.started_at.isoformat(),
                result.duration_seconds or 0,
                result.tests_passed or 0,
                result.tests_failed or 0,
                result.tests_total or 0,
                round(result.pass_rate, 1),
                'Yes' if result.is_suite_run else 'No',
                result.executed_by.username if result.executed_by else 'Unknown',
                'Yes' if result.headless else 'No'
            ])
        
        return csv_data
