
import os
import re
import logging
from pathlib import Path

def convert_playwright_to_robot(playwright_script_path, output_path=None):
    """Convert Playwright script to Robot Framework"""
    if not os.path.exists(playwright_script_path):
        raise FileNotFoundError(f"Playwright script not found: {playwright_script_path}")
    
    try:
        with open(playwright_script_path, 'r', encoding='utf-8') as f:
            playwright_content = f.read()
        
        # Basic conversion logic
        robot_content = convert_playwright_content(playwright_content)
        
        # Determine output path
        if not output_path:
            script_name = Path(playwright_script_path).stem
            output_dir = os.path.dirname(playwright_script_path).replace('playwright_scripts', 'robot_scripts')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{script_name}.robot")
        
        # Write converted content
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(robot_content)
        
        return output_path, None  # Return path and error (None for success)
        
    except Exception as e:
        logging.error(f"Conversion failed for {playwright_script_path}: {e}")
        return None, str(e)

def convert_playwright_content(playwright_content):
    """Convert Playwright Python code to Robot Framework syntax"""
    robot_lines = []
    
    # Add header
    robot_lines.extend([
        "*** Settings ***",
        "Library    Browser",
        "",
        "*** Test Cases ***",
        "Test Case",
        ""
    ])
    
    # Parse Playwright commands
    lines = playwright_content.split('\n')
    in_test_function = False
    
    for line in lines:
        line = line.strip()
        
        if 'def run(' in line or 'def test_' in line:
            in_test_function = True
            continue
        
        if not in_test_function or not line or line.startswith('#') or line.startswith('import'):
            continue
        
        # Convert common Playwright commands to Robot Framework
        robot_line = convert_playwright_line(line)
        if robot_line:
            robot_lines.append(f"    {robot_line}")
    
    return '\n'.join(robot_lines)

def convert_playwright_line(line):
    """Convert a single Playwright line to Robot Framework"""
    line = line.strip()
    
    # Remove common Python syntax
    if line.endswith(';'):
        line = line[:-1]
    
    # Browser launch
    if 'playwright.chromium.launch' in line:
        return "New Browser    chromium    headless=False"
    elif 'browser.new_context' in line:
        return "New Context"
    elif 'context.new_page' in line:
        return "New Page"
    
    # Navigation
    elif '.goto(' in line:
        url_match = re.search(r'\.goto\(["\']([^"\']+)["\']', line)
        if url_match:
            return f"Go To    {url_match.group(1)}"
    
    # Clicks
    elif '.click(' in line:
        selector_match = re.search(r'\.click\(["\']([^"\']+)["\']', line)
        if selector_match:
            return f"Click    {selector_match.group(1)}"
        role_match = re.search(r'get_by_role\(["\']([^"\']+)["\'],\s*name=["\']([^"\']+)["\']', line)
        if role_match:
            return f"Click    role={role_match.group(1)}[name=\"{role_match.group(2)}\"]"
    
    # Text input
    elif '.fill(' in line:
        parts = re.search(r'\.fill\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']', line)
        if parts:
            return f"Fill Text    {parts.group(1)}    {parts.group(2)}"
    
    # Wait operations
    elif '.wait_for_' in line:
        return "Sleep    1s"
    
    # Close operations
    elif '.close()' in line:
        if 'context' in line:
            return "Close Context"
        elif 'browser' in line:
            return "Close Browser"
    
    # Default: comment out unrecognized lines
    return f"# {line}"

def validate_robot_script(robot_script_path):
    """Validate Robot Framework script syntax"""
    try:
        from robot.api import get_model
        
        if not os.path.exists(robot_script_path):
            return False, "Script file not found"
        
        # Try to parse the robot file
        model = get_model(robot_script_path)
        
        # Basic validation
        if not model.sections:
            return False, "No sections found in Robot script"
        
        has_test_cases = any(section.header.type == 'TEST CASE' for section in model.sections)
        if not has_test_cases:
            return False, "No test cases found in Robot script"
        
        return True, "Valid Robot Framework script"
        
    except ImportError:
        # Robot Framework not installed, skip validation
        return True, "Robot Framework not available for validation"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

def get_conversion_status(script_id):
    """Get conversion status for a script"""
    from app.models import TestScript
    
    script = TestScript.query.get(script_id)
    if not script:
        return None
    
    return {
        'script_id': script_id,
        'status': script.conversion_status,
        'error': script.conversion_error,
        'playwright_path': script.playwright_script_path,
        'robot_path': script.robot_script_path,
        'logs': script.conversion_logs
    }
