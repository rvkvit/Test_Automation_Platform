import os
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from app import db
from app.models import ExecutionResult, ExecutionStatus, TestScript

def execute_script_async(script_id, user_id, headless=True):
    """Execute a script asynchronously"""
    try:
        script = TestScript.query.get(script_id)
        if not script:
            return

        executor = RobotFrameworkExecutor(script.project, headless=headless)
        from app.models import User
        user = User.query.get(user_id)
        executor.execute_script(script, user)
    except Exception as e:
        print(f"Error in async execution: {e}")

def execute_suite_async(project_id, user_id, script_ids=None, headless=True):
    """Execute a suite of scripts asynchronously"""
    try:
        from app.models import Project, User
        project = Project.query.get(project_id)
        user = User.query.get(user_id)

        if not project or not user:
            return

        if script_ids:
            scripts = TestScript.query.filter(
                TestScript.id.in_(script_ids),
                TestScript.project_id == project.id
            ).all()
        else:
            scripts = TestScript.query.filter_by(project_id=project.id).all()

        executor = RobotFrameworkExecutor(project, headless=headless)
        executor.execute_suite(scripts, user)
    except Exception as e:
        print(f"Error in async suite execution: {e}")

class RobotFrameworkExecutor:
    def __init__(self, project, headless=True):
        self.project = project
        self.headless = headless

    def execute_script(self, script, user):
        """Execute a single script"""
        execution = ExecutionResult(
            project_id=script.project_id,
            script_id=script.id,
            status=ExecutionStatus.RUNNING,
            executed_by_id=user.id,
            started_at=datetime.now(timezone.utc)
        )

        db.session.add(execution)
        db.session.commit()

        try:
            # Simulate execution (replace with actual Robot Framework execution)
            import time
            time.sleep(2)  # Simulate execution time

            execution.status = ExecutionStatus.PASSED
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_seconds = 2.0
            execution.tests_total = 1
            execution.tests_passed = 1
            execution.tests_failed = 0
            execution.pass_rate = 100.0

            db.session.commit()

        except Exception as e:
            execution.status = ExecutionStatus.ERROR
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            db.session.commit()

        return execution

    def execute_suite(self, scripts, user):
        """Execute a suite of scripts"""
        execution = ExecutionResult(
            project_id=self.project.id,
            status=ExecutionStatus.RUNNING,
            executed_by_id=user.id,
            started_at=datetime.now(timezone.utc)
        )

        db.session.add(execution)
        db.session.commit()

        try:
            # Simulate suite execution
            import time
            time.sleep(len(scripts) * 2)  # Simulate execution time

            execution.status = ExecutionStatus.PASSED
            execution.completed_at = datetime.now(timezone.utc)
            execution.duration_seconds = len(scripts) * 2.0
            execution.tests_total = len(scripts)
            execution.tests_passed = len(scripts)
            execution.tests_failed = 0
            execution.pass_rate = 100.0

            db.session.commit()

        except Exception as e:
            execution.status = ExecutionStatus.ERROR
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            db.session.commit()

        return execution