import os
import subprocess
import threading
import signal
import psutil
from pathlib import Path
from app.utils.fs import ensure_directory, sanitize_filename
from app.utils.environment import get_runtime_info
import logging

logger = logging.getLogger(__name__)

class PlaywrightRecorder:
    def __init__(self, project_name, script_name, browser_type='chromium', base_url=None):
        self.project_name = sanitize_filename(project_name)
        self.script_name = sanitize_filename(script_name)
        self.browser_type = browser_type
        self.base_url = base_url
        self.process = None
        self.output_file = None
        self.is_recording = False
        
        # Setup paths
        from app.config import Config
        self.root_path = Config.TEST_APP_ROOT
        self.scripts_dir = self.root_path / 'playwright_scripts' / self.project_name
        ensure_directory(self.scripts_dir)
        
        # Generate unique filename if collision exists
        base_filename = f"{self.script_name}.py"
        counter = 1
        while (self.scripts_dir / base_filename).exists():
            base_filename = f"{self.script_name}_v{counter}.py"
            counter += 1
        
        self.output_file = self.scripts_dir / base_filename
        self.final_script_name = base_filename[:-3]  # Remove .py extension
    
    def start_recording(self):
        """Start Playwright codegen recording session"""
        try:
            runtime_info = get_runtime_info()
            
            # Prepare codegen command
            cmd = [
                'python', '-m', 'playwright', 'codegen',
                '--target', 'python',
                '--browser', self.browser_type,
                '-o', str(self.output_file)
            ]
            
            # Add headless flag if in CI environment
            if runtime_info['is_headless']:
                cmd.extend(['--device', 'Desktop Chrome'])
            
            # Add base_url if provided
            if self.base_url:
                cmd.append(self.base_url)
            
            logger.info(f"Starting Playwright codegen: {' '.join(cmd)}")
            
            # Start the process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if not runtime_info['is_windows'] else None,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if runtime_info['is_windows'] else 0
            )
            
            self.is_recording = True
            logger.info(f"Playwright codegen started with PID: {self.process.pid}")
            
            return {
                'success': True,
                'pid': self.process.pid,
                'output_file': str(self.output_file),
                'script_name': self.final_script_name
            }
            
        except Exception as e:
            logger.error(f"Failed to start Playwright recording: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def stop_recording(self):
        """Stop the recording session and finalize the script"""
        try:
            if not self.process or not self.is_recording:
                return {'success': False, 'error': 'No active recording session'}
            
            runtime_info = get_runtime_info()
            
            # Terminate the process gracefully
            if runtime_info['is_windows']:
                self.process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                os.killpg(os.getpgid(self.process.pid), signal.SIGTERM)
            
            # Wait for process to terminate
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                logger.warning("Process didn't terminate gracefully, forcing kill")
                if runtime_info['is_windows']:
                    self.process.kill()
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
                self.process.wait()
            
            self.is_recording = False
            
            # Check if output file was created and has content
            if self.output_file.exists() and self.output_file.stat().st_size > 0:
                # Read and clean up the generated script
                script_content = self._cleanup_generated_script()
                
                return {
                    'success': True,
                    'script_content': script_content,
                    'output_file': str(self.output_file),
                    'script_name': self.final_script_name
                }
            else:
                return {
                    'success': False,
                    'error': 'No script content was generated'
                }
                
        except Exception as e:
            logger.error(f"Failed to stop recording: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _cleanup_generated_script(self):
        """Clean up and enhance the generated Playwright script"""
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Basic cleanup and enhancements
            lines = content.split('\n')
            cleaned_lines = []
            
            for line in lines:
                # Skip empty lines at the beginning
                if not cleaned_lines and not line.strip():
                    continue
                
                # Add comments for better readability
                if 'page.goto(' in line:
                    cleaned_lines.append('    # Navigate to the target URL')
                elif 'page.click(' in line:
                    cleaned_lines.append('    # Click element')
                elif 'page.fill(' in line:
                    cleaned_lines.append('    # Fill form field')
                elif 'expect(' in line:
                    cleaned_lines.append('    # Verify expected result')
                
                cleaned_lines.append(line)
            
            # Write back the cleaned content
            cleaned_content = '\n'.join(cleaned_lines)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            return cleaned_content
            
        except Exception as e:
            logger.error(f"Failed to cleanup script: {str(e)}")
            # Return original content if cleanup fails
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                return ""
    
    def get_status(self):
        """Get current recording status"""
        if not self.process:
            return {'is_recording': False, 'status': 'not_started'}
        
        if self.process.poll() is None:
            return {'is_recording': True, 'status': 'recording', 'pid': self.process.pid}
        else:
            return {'is_recording': False, 'status': 'completed'}
    
    def cleanup(self):
        """Cleanup resources"""
        if self.process and self.process.poll() is None:
            try:
                runtime_info = get_runtime_info()
                if runtime_info['is_windows']:
                    self.process.kill()
                else:
                    os.killpg(os.getpgid(self.process.pid), signal.SIGKILL)
            except:
                pass
        self.is_recording = False

# Global registry for active recording sessions
_active_recordings = {}

def start_recording_session(project_name, script_name, browser_type='chromium', base_url=None):
    """Start a new recording session"""
    session_key = f"{project_name}_{script_name}"
    
    # Stop any existing session with the same key
    if session_key in _active_recordings:
        _active_recordings[session_key].cleanup()
    
    # Create new recorder
    recorder = PlaywrightRecorder(project_name, script_name, browser_type, base_url)
    result = recorder.start_recording()
    
    if result['success']:
        _active_recordings[session_key] = recorder
    
    return result

def stop_recording_session(project_name, script_name):
    """Stop an active recording session"""
    session_key = f"{project_name}_{script_name}"
    
    if session_key not in _active_recordings:
        return {'success': False, 'error': 'No active recording session found'}
    
    recorder = _active_recordings[session_key]
    result = recorder.stop_recording()
    
    # Cleanup the session
    del _active_recordings[session_key]
    
    return result

def get_recording_status(project_name, script_name):
    """Get status of a recording session"""
    session_key = f"{project_name}_{script_name}"
    
    if session_key not in _active_recordings:
        return {'is_recording': False, 'status': 'not_found'}
    
    return _active_recordings[session_key].get_status()

def cleanup_all_sessions():
    """Cleanup all active recording sessions"""
    for recorder in _active_recordings.values():
        recorder.cleanup()
    _active_recordings.clear()
