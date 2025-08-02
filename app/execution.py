
import os
import subprocess
import logging
from datetime import datetime, timezone
from app import db
from app.models import ExecutionResult, TestScript, ExecutionStatus
from pathlib import Path

def execute_robot_script(script_id, headless=True, user_id=None):
    """Execute a Robot Framework script"""
    script = TestScript.query.get(script_id)
    if not script:
        raise ValueError(f"Script with ID {script_id} not found")
    
    if not script.robot_script_path or not os.path.exists(script.robot_script_path):
        raise ValueError(f"Robot script file not found: {script.robot_script_path}")
    
    # Create execution result record
    execution = ExecutionResult(
        project_id=script.project_id,
        script_id=script_id,
        status=ExecutionStatus.RUNNING,
        executed_by_id=user_id,
        headless=headless
    )
    db.session.add(execution)
    db.session.commit()
    
    try:
        # Prepare output directory
        output_dir = f"results/execution_{execution.id}"
        os.makedirs(output_dir, exist_ok=True)
        
        # Build robot command
        cmd = [
            'robot',
            '--outputdir', output_dir,
            '--log', f'{output_dir}/log.html',
            '--report', f'{output_dir}/report.html',
            '--output', f'{output_dir}/output.xml',
            script.robot_script_path
        ]
        
        # Execute robot framework
        start_time = datetime.now(timezone.utc)
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        end_time = datetime.now(timezone.utc)
        
        # Update execution result
        execution.completed_at = end_time
        execution.duration_seconds = (end_time - start_time).total_seconds()
        execution.log_path = f'{output_dir}/log.html'
        execution.report_path = f'{output_dir}/report.html'
        execution.output_xml_path = f'{output_dir}/output.xml'
        
        # Parse results from output.xml if available
        if os.path.exists(f'{output_dir}/output.xml'):
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(f'{output_dir}/output.xml')
                root = tree.getroot()
                
                stats = root.find('.//statistics/total/stat[@pass]')
                if stats is not None:
                    execution.tests_passed = int(stats.get('pass', 0))
                    execution.tests_failed = int(stats.get('fail', 0))
                    execution.tests_total = execution.tests_passed + execution.tests_failed
                    execution.pass_rate = (execution.tests_passed / execution.tests_total * 100) if execution.tests_total > 0 else 0
            except Exception as e:
                logging.error(f"Failed to parse output.xml: {e}")
        
        # Determine status based on return code
        if result.returncode == 0:
            execution.status = ExecutionStatus.PASSED
        else:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = result.stderr or result.stdout
        
        db.session.commit()
        return execution
        
    except subprocess.TimeoutExpired:
        execution.status = ExecutionStatus.ERROR
        execution.error_message = "Execution timed out"
        execution.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        raise
    except Exception as e:
        execution.status = ExecutionStatus.ERROR
        execution.error_message = str(e)
        execution.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        raise

def execute_project_suite(project_id, headless=True, user_id=None):
    """Execute all scripts in a project as a suite"""
    from app.models import Project
    
    project = Project.query.get(project_id)
    if not project:
        raise ValueError(f"Project with ID {project_id} not found")
    
    # Create suite execution record
    execution = ExecutionResult(
        project_id=project_id,
        status=ExecutionStatus.RUNNING,
        executed_by_id=user_id,
        is_suite_run=True,
        headless=headless
    )
    db.session.add(execution)
    db.session.commit()
    
    try:
        start_time = datetime.now(timezone.utc)
        results = []
        
        # Execute each script
        for script in project.scripts:
            if script.robot_script_path and os.path.exists(script.robot_script_path):
                try:
                    script_result = execute_robot_script(script.id, headless, user_id)
                    results.append(script_result)
                except Exception as e:
                    logging.error(f"Failed to execute script {script.id}: {e}")
        
        # Aggregate results
        end_time = datetime.now(timezone.utc)
        execution.completed_at = end_time
        execution.duration_seconds = (end_time - start_time).total_seconds()
        
        total_passed = sum(r.tests_passed or 0 for r in results)
        total_failed = sum(r.tests_failed or 0 for r in results)
        total_tests = total_passed + total_failed
        
        execution.tests_passed = total_passed
        execution.tests_failed = total_failed
        execution.tests_total = total_tests
        execution.pass_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Determine overall status
        if total_failed == 0 and total_tests > 0:
            execution.status = ExecutionStatus.PASSED
        elif total_tests > 0:
            execution.status = ExecutionStatus.FAILED
        else:
            execution.status = ExecutionStatus.ERROR
            execution.error_message = "No tests executed"
        
        db.session.commit()
        return execution
        
    except Exception as e:
        execution.status = ExecutionStatus.ERROR
        execution.error_message = str(e)
        execution.completed_at = datetime.now(timezone.utc)
        db.session.commit()
        raise

def get_execution_status(execution_id):
    """Get execution status"""
    execution = ExecutionResult.query.get(execution_id)
    if not execution:
        return None
    
    return {
        'id': execution.id,
        'status': execution.status.value,
        'progress': 100 if execution.completed_at else 50,
        'started_at': execution.started_at.isoformat() if execution.started_at else None,
        'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
        'duration': execution.duration_seconds,
        'tests_total': execution.tests_total,
        'tests_passed': execution.tests_passed,
        'tests_failed': execution.tests_failed,
        'pass_rate': execution.pass_rate,
        'error_message': execution.error_message
    }
