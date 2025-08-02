import os
import platform
from pathlib import Path

def get_runtime_info():
    """
    Get runtime environment information for cross-platform compatibility
    """
    system = platform.system().lower()
    
    return {
        'is_windows': system.startswith('win'),
        'is_linux': system == 'linux',
        'is_macos': system == 'darwin',
        'is_headless': os.getenv('HEADLESS', '1') == '1',
        'data_root': Path(os.getenv('TEST_APP_ROOT', Path(__file__).parent.parent.parent)),
        'python_executable': 'python',  # Could be 'python3' on some systems
        'system': system,
        'architecture': platform.machine(),
        'python_version': platform.python_version()
    }

def get_browser_executable_path(browser_type='chromium'):
    """
    Get the path to browser executable for different platforms
    """
    runtime_info = get_runtime_info()
    
    # Playwright installs browsers in a standard location
    # This is just for reference - Playwright handles this automatically
    browser_paths = {
        'chromium': {
            'windows': 'chromium.exe',
            'linux': 'chromium',
            'darwin': 'Chromium.app/Contents/MacOS/Chromium'
        },
        'firefox': {
            'windows': 'firefox.exe',
            'linux': 'firefox',
            'darwin': 'Firefox.app/Contents/MacOS/firefox'
        },
        'webkit': {
            'windows': 'MiniBrowser.exe',
            'linux': 'MiniBrowser',
            'darwin': 'MiniBrowser'
        }
    }
    
    if browser_type not in browser_paths:
        return None
    
    system_key = runtime_info['system']
    if system_key == 'darwin':
        system_key = 'darwin'
    elif runtime_info['is_windows']:
        system_key = 'windows'
    else:
        system_key = 'linux'
    
    return browser_paths[browser_type].get(system_key)

def setup_environment_variables():
    """
    Setup environment variables for consistent cross-platform operation
    """
    runtime_info = get_runtime_info()
    
    # Set PYTHONPATH to include the application root
    current_pythonpath = os.environ.get('PYTHONPATH', '')
    app_root = str(runtime_info['data_root'])
    
    if app_root not in current_pythonpath:
        if current_pythonpath:
            os.environ['PYTHONPATH'] = f"{app_root}{os.pathsep}{current_pythonpath}"
        else:
            os.environ['PYTHONPATH'] = app_root
    
    # Set NODE_OPTIONS for headless environments (if using Node.js tools)
    if runtime_info['is_headless']:
        os.environ['NODE_OPTIONS'] = os.environ.get('NODE_OPTIONS', '') + ' --max-old-space-size=4096'
    
    # Set display for Linux headless environments
    if runtime_info['is_linux'] and runtime_info['is_headless']:
        if 'DISPLAY' not in os.environ:
            os.environ['DISPLAY'] = ':99'
    
    return runtime_info

def check_system_dependencies():
    """
    Check if required system dependencies are available
    """
    dependencies = {
        'python': True,  # We're running Python, so this is available
        'playwright': False,
        'robot': False,
        'ffmpeg': False
    }
    
    try:
        import playwright
        dependencies['playwright'] = True
    except ImportError:
        pass
    
    try:
        import robot
        dependencies['robot'] = True
    except ImportError:
        pass
    
    # Check for FFmpeg (used by Playwright for video recording)
    import subprocess
    try:
        subprocess.run(['ffmpeg', '-version'], 
                      capture_output=True, check=True, timeout=5)
        dependencies['ffmpeg'] = True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    return dependencies

def get_recommended_browser_args(headless=True):
    """
    Get recommended browser arguments for different environments
    """
    runtime_info = get_runtime_info()
    
    base_args = [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--no-first-run',
        '--disable-background-timer-throttling',
        '--disable-backgrounding-occluded-windows',
        '--disable-renderer-backgrounding'
    ]
    
    if headless:
        base_args.append('--headless')
    
    # Platform-specific arguments
    if runtime_info['is_linux']:
        base_args.extend([
            '--disable-software-rasterizer',
            '--disable-background-networking'
        ])
    
    if runtime_info['is_windows']:
        base_args.extend([
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection'
        ])
    
    return base_args

def get_temp_directory():
    """
    Get appropriate temporary directory for the platform
    """
    import tempfile
    return Path(tempfile.gettempdir()) / 'test_automation_platform'

def ensure_playwright_browsers():
    """
    Ensure Playwright browsers are installed
    """
    try:
        import subprocess
        result = subprocess.run([
            'python', '-m', 'playwright', 'install', '--with-deps'
        ], capture_output=True, text=True, timeout=300)
        
        return {
            'success': result.returncode == 0,
            'output': result.stdout,
            'error': result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Browser installation timed out'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def detect_container_environment():
    """
    Detect if running in a container environment
    """
    indicators = [
        os.path.exists('/.dockerenv'),
        os.path.exists('/proc/1/cgroup') and 'docker' in open('/proc/1/cgroup').read(),
        os.environ.get('container') is not None,
        os.environ.get('KUBERNETES_SERVICE_HOST') is not None
    ]
    
    return any(indicators)

def get_system_info():
    """
    Get comprehensive system information for diagnostics
    """
    # Add missing imports for referenced functions
    from app.utils.environment import get_runtime_info, check_system_dependencies, detect_container_environment, get_temp_directory
    
    runtime_info = get_runtime_info()
    dependencies = check_system_dependencies()
    
    return {
        'runtime': runtime_info,
        'dependencies': dependencies,
        'container': detect_container_environment(),
        'temp_dir': str(get_temp_directory()),
        'env_vars': {
            'HEADLESS': os.environ.get('HEADLESS', 'not set'),
            'DISPLAY': os.environ.get('DISPLAY', 'not set'),
            'TEST_APP_ROOT': os.environ.get('TEST_APP_ROOT', 'not set'),
            'PYTHONPATH': os.environ.get('PYTHONPATH', 'not set')
        }
    }
