import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from flask import current_app
from app import create_app
from robot import run_cli
from robot.api import get_model
import logging

from app import db
from app.models import ExecutionResult, ExecutionStatus, TestScript
from app.utils.fs import ensure_directory, sanitize_filename
from app.utils.environment import get_runtime_info
from app.config import Config

logger = logging.getLogger(__name__)

class RobotFrameworkExecutor:
    def __init__(self, project, headless=True):
        self.project = project
        self.headless = headless
        self.runtime_info = get_runtime_info()
        
        # Setup paths
        self.results_dir = Config.TEST_APP_ROOT / 'results' / sanitize_filename(project.name)
        self.videos_base_dir = Config.TEST_APP_ROOT / 'execution_videos' / sanitize_filename(project.name)
        ensure_directory(self.results_dir)
        ensure_directory(self.videos_base_dir)
    
    def execute_script(self, script, executed_by):
        """Execute a single Robot Framework script"""
        logger.info(f"Starting execution of script: {script.name}")
        
        # Create execution result record
        execution = ExecutionResult(
            project_id=self.project.id,
            script_id=script.id,
            status=ExecutionStatus.PENDING,
            executed_by_id=executed_by.id,
            is_suite_run=False,
            headless=self.headless
        )
        db.session.add(execution)
        db.session.commit()
        
        try:
            # Update status to running
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)
            db.session.commit()

            # Execute the script
            result = self._run_robot_script(script, execution)

            # Update execution record with results
            execution.completed_at = datetime.now(timezone.utc)
            # Ensure both datetimes are timezone-aware before subtraction
            started_at = execution.started_at
            completed_at = execution.completed_at
            if started_at and completed_at:
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                execution.duration_seconds = (completed_at - started_at).total_seconds()

            if result['success']:
                execution.status = ExecutionStatus.PASSED if result['all_passed'] else ExecutionStatus.FAILED
                execution.tests_passed = result['tests_passed']
                execution.tests_failed = result['tests_failed']
                execution.tests_total = result['tests_total']
                execution.log_path = result.get('log_path')
                execution.report_path = result.get('report_path')
                execution.output_xml_path = result.get('output_xml_path')
                # Store video_path as relative to TEST_APP_ROOT for streaming
                abs_video_path = result.get('video_path')
                if abs_video_path and str(Config.TEST_APP_ROOT) in abs_video_path:
                    rel_video_path = abs_video_path.replace(str(Config.TEST_APP_ROOT), '').lstrip(r'\/')
                    execution.video_path = rel_video_path
                else:
                    execution.video_path = abs_video_path
            else:
                execution.status = ExecutionStatus.ERROR
                execution.error_message = result['error']

            db.session.commit()
            logger.info(f"Script execution completed: {execution.status.value}")

            return execution

        except Exception as e:
            logger.error(f"Script execution failed: {str(e)}")
            execution.status = ExecutionStatus.ERROR
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            started_at = execution.started_at
            completed_at = execution.completed_at
            if started_at and completed_at:
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                execution.duration_seconds = (completed_at - started_at).total_seconds()
            db.session.commit()
            return execution
    
    def execute_suite(self, scripts, executed_by):
        """Execute multiple scripts as a suite"""
        logger.info(f"Starting suite execution with {len(scripts)} scripts")
        
        # Create suite execution result record
        execution = ExecutionResult(
            project_id=self.project.id,
            script_id=None,  # No specific script for suite runs
            status=ExecutionStatus.PENDING,
            executed_by_id=executed_by.id,
            is_suite_run=True,
            headless=self.headless
        )
        db.session.add(execution)
        db.session.commit()
        
        try:
            execution.status = ExecutionStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)
            db.session.commit()

            # Execute all scripts in the suite
            result = self._run_robot_suite(scripts, execution)

            # Update execution record
            execution.completed_at = datetime.now(timezone.utc)
            started_at = execution.started_at
            completed_at = execution.completed_at
            if started_at and completed_at:
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                execution.duration_seconds = (completed_at - started_at).total_seconds()

            if result['success']:
                execution.status = ExecutionStatus.PASSED if result['all_passed'] else ExecutionStatus.FAILED
                execution.tests_passed = result['tests_passed']
                execution.tests_failed = result['tests_failed']
                execution.tests_total = result['tests_total']
                execution.log_path = result.get('log_path')
                execution.report_path = result.get('report_path')
                execution.output_xml_path = result.get('output_xml_path')
            else:
                execution.status = ExecutionStatus.ERROR
                execution.error_message = result['error']

            db.session.commit()
            logger.info(f"Suite execution completed: {execution.status.value}")

            return execution

        except Exception as e:
            logger.error(f"Suite execution failed: {str(e)}")
            execution.status = ExecutionStatus.ERROR
            execution.error_message = str(e)
            execution.completed_at = datetime.now(timezone.utc)
            started_at = execution.started_at
            completed_at = execution.completed_at
            if started_at and completed_at:
                if started_at.tzinfo is None:
                    started_at = started_at.replace(tzinfo=timezone.utc)
                if completed_at.tzinfo is None:
                    completed_at = completed_at.replace(tzinfo=timezone.utc)
                execution.duration_seconds = (completed_at - started_at).total_seconds()
            db.session.commit()
            return execution
    
    def _run_robot_script(self, script, execution):
        """Run a single Robot Framework script"""
        try:
            if not script.robot_script_path or not Path(script.robot_script_path).exists():
                return {
                    'success': False,
                    'error': 'Robot Framework script file not found'
                }
            
            # Create execution-specific output directory
            run_id = f"run_{execution.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_dir = self.results_dir / run_id
            ensure_directory(output_dir)
            
            # Prepare Robot Framework arguments
            robot_args = self._build_robot_args(script, output_dir)
            robot_args.append(script.robot_script_path)
            
            # Run Robot Framework
            return_code = run_cli(robot_args, exit=False)
            
            # Parse results
            result = self._parse_robot_results(output_dir, return_code)
            
            # Handle video if generated
            video_path = self._handle_video_output(script, output_dir)
            if video_path:
                result['video_path'] = video_path
            
            return result
            
        except Exception as e:
            logger.error(f"Robot script execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _run_robot_suite(self, scripts, execution):
        """Run multiple Robot Framework scripts as a suite"""
        try:
            # Filter scripts that have robot files
            valid_scripts = [s for s in scripts if s.robot_script_path and Path(s.robot_script_path).exists()]
            
            if not valid_scripts:
                return {
                    'success': False,
                    'error': 'No valid Robot Framework scripts found'
                }
            
            # Create execution-specific output directory
            run_id = f"suite_{execution.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_dir = self.results_dir / run_id
            ensure_directory(output_dir)
            
            # Prepare Robot Framework arguments for suite
            robot_args = self._build_robot_args(None, output_dir)
            
            # Add all script paths
            for script in valid_scripts:
                robot_args.append(script.robot_script_path)
            
            # Run Robot Framework
            return_code = run_cli(robot_args, exit=False)
            
            # Parse results
            result = self._parse_robot_results(output_dir, return_code)
            
            return result
            
        except Exception as e:
            logger.error(f"Robot suite execution error: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _build_robot_args(self, script, output_dir):
        """Build Robot Framework command line arguments"""
        args = [
            '--outputdir', str(output_dir),
            '--pythonpath', str(Config.TEST_APP_ROOT),
        ]
        
        # Add browser library specific variables
        if self.headless:
            args.extend(['--variable', 'HEADLESS:True'])
        else:
            args.extend(['--variable', 'HEADLESS:False'])
        
        # Add project-specific variables
        if self.project.base_url:
            args.extend(['--variable', f'BASE_URL:{self.project.base_url}'])
        
        # Browser selection
        browser_type = script.browser_type if script else 'chromium'
        args.extend(['--variable', f'BROWSER:{browser_type}'])
        
        # Timeout settings
        args.extend(['--variable', 'TIMEOUT:30s'])
        
        # Video recording for Browser Library
        if not self.headless:
            args.extend(['--variable', 'RECORD_VIDEO:True'])
        
        # Include/exclude tags if specified
        if script and script.tags:
            tags = script.get_tags_list()
            if tags:
                args.extend(['--include'] + tags)
        
        # Set log level
        args.extend(['--loglevel', 'INFO'])
        
        return args
    
    def _parse_robot_results(self, output_dir, return_code):
        """Parse Robot Framework execution results"""
        try:
            output_xml = output_dir / 'output.xml'
            log_html = output_dir / 'log.html'
            report_html = output_dir / 'report.html'
            
            result = {
                'success': True,
                'return_code': return_code,
                'tests_passed': 0,
                'tests_failed': 0,
                'tests_total': 0,
                'all_passed': return_code == 0
            }
            
            # Set file paths if they exist
            if output_xml.exists():
                result['output_xml_path'] = str(output_xml)
            if log_html.exists():
                result['log_path'] = str(log_html)
            if report_html.exists():
                result['report_path'] = str(report_html)
            
            # Parse output.xml for detailed statistics
            if output_xml.exists():
                try:
                    model = get_model(str(output_xml))
                    suite = model.suites[0] if model.suites else None
                    
                    if suite:
                        stats = suite.statistics
                        result['tests_total'] = stats.total
                        result['tests_passed'] = stats.passed
                        result['tests_failed'] = stats.failed
                        result['all_passed'] = stats.failed == 0
                        
                except Exception as e:
                    logger.warning(f"Failed to parse output.xml: {str(e)}")
                    # Fallback to return code
                    result['tests_total'] = 1
                    result['tests_passed'] = 1 if return_code == 0 else 0
                    result['tests_failed'] = 0 if return_code == 0 else 1
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to parse Robot results: {str(e)}")
            return {
                'success': False,
                'error': f'Failed to parse results: {str(e)}'
            }
    
    def _handle_video_output(self, script, output_dir):
        """Handle video output from Browser Library"""
        try:
            # Look for video files in the output directory
            video_files = list(output_dir.glob('*.webm'))
            if not video_files:
                video_files = list(output_dir.glob('*.mp4'))
            
            if video_files:
                # Use the first video file found
                source_video = video_files[0]
                # If video is already saved in the correct folder, just return its relative path
                rel_path = str(source_video.relative_to(Config.TEST_APP_ROOT))
                return rel_path
            return None
            
        except Exception as e:
            logger.warning(f"Failed to handle video output: {str(e)}")
            return None

def execute_script_async(script_id, user_id, headless=True):
    app = current_app._get_current_object() if current_app else create_app()
    with app.app_context():
        """Background task for executing a script"""
        try:
            from app.models import User
            
            script = TestScript.query.get(script_id)
            user = User.query.get(user_id)
            
            if not script or not user:
                logger.error(f"Script {script_id} or user {user_id} not found")
                return
            
            executor = RobotFrameworkExecutor(script.project, headless=headless)
            execution = executor.execute_script(script, user)
            
            logger.info(f"Async execution completed for script {script_id}: {execution.status.value}")
            return execution
            
        except Exception as e:
            logger.error(f"Background execution failed for script {script_id}: {str(e)}")

def execute_suite_async(project_id, user_id, script_ids=None, headless=True):
    app = current_app._get_current_object() if current_app else create_app()
    with app.app_context():
        """Background task for executing a project suite"""
        try:
            from app.models import User, Project
            
            project = Project.query.get(project_id)
            user = User.query.get(user_id)
            
            if not project or not user:
                logger.error(f"Project {project_id} or user {user_id} not found")
                return
            
            # Get scripts to execute
            if script_ids:
                scripts = TestScript.query.filter(
                    TestScript.id.in_(script_ids),
                    TestScript.project_id == project_id
                ).all()
            else:
                scripts = project.test_scripts
            
            # Filter only converted scripts
            scripts = [s for s in scripts if s.conversion_status == 'completed']
            
            if not scripts:
                logger.warning(f"No executable scripts found for project {project_id}")
                return
            
            executor = RobotFrameworkExecutor(project, headless=headless)
            execution = executor.execute_suite(scripts, user)
            
            logger.info(f"Async suite execution completed for project {project_id}: {execution.status.value}")
            return execution
            
        except Exception as e:
            logger.error(f"Background suite execution failed for project {project_id}: {str(e)}")
