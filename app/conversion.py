import json
import logging
import os
import requests
from pathlib import Path
from app.config import Config
from app.utils.fs import ensure_directory, sanitize_filename

logger = logging.getLogger(__name__)

class PlaywrightToRobotConverter:
    def __init__(self):
        # Always read env variables inside constructor
        self.endpoint = os.environ.get('AZURE_OPENAI_ENDPOINT')
        self.api_key = os.environ.get('AZURE_OPENAI_API_KEY')
        self.deployment = os.environ.get('AZURE_OPENAI_DEPLOYMENT') or "gpt-4o"
        # Debug: print env variables here
        logger.debug(f"PlaywrightToRobotConverter __init__ AZURE_OPENAI_ENDPOINT: {self.endpoint}")
        logger.debug(f"PlaywrightToRobotConverter __init__ AZURE_OPENAI_API_KEY: {self.api_key}")
        logger.debug(f"PlaywrightToRobotConverter __init__ AZURE_OPENAI_DEPLOYMENT: {self.deployment}")
        self.is_configured = bool(self.endpoint and self.api_key)
        if not self.is_configured:
            logger.warning("Azure OpenAI configuration missing. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables to enable AI generation.")

    def check_configuration(self):
        if not self.is_configured:
            raise RuntimeError("Azure OpenAI is not configured. Please provide AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables.")
    
    def convert_playwright_to_robot(self, playwright_script, project_metadata=None):
        """Convert Playwright script to Robot Framework format using Azure OpenAI"""
        if not self.endpoint or not self.api_key or not self.deployment:
            return {
                'success': False,
                'error': 'Azure OpenAI credentials not configured. Please check your API credentials.'
            }
        try:
            system_prompt = self._get_conversion_system_prompt()
            user_prompt = self._build_user_prompt(playwright_script, project_metadata)
            url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version=2024-06-01"
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key
            }
            payload = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.1,
                "max_tokens": 4000,
                "response_format": {"type": "json_object"}
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code != 200:
                logger.error(f"Azure OpenAI API error: {response.status_code} {response.text}")
                return {
                    'success': False,
                    'error': f'Azure OpenAI API error: {response.status_code} {response.text}'
                }
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            result = json.loads(content)
            if 'robot_code' not in result:
                return {
                    'success': False,
                    'error': 'Invalid response format from AI service'
                }
            robot_script = self._enhance_robot_script(result['robot_code'], project_metadata)
            return {
                'success': True,
                'robot_script': robot_script,
                'explanation': result.get('explanation', ''),
                'warnings': result.get('warnings', []),
                'ai_prompt': user_prompt,
                'ai_response': content
            }
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            return {
                'success': False,
                'error': f'AI conversion failed: {str(e)}'
            }
    
    def _get_conversion_system_prompt(self):
        """Get the system prompt for conversion"""
        return """
You are an expert in Robot Framework using the Browser Library (based on Playwright).

Convert the following Python Playwright code into a modular Robot Framework test with the following constraints:

1. Use the Browser Library.
2. Structure the output into:
   - *** Settings ***
   - *** Variables ***
   - *** Test Cases ***
   - *** Keywords ***
3. Use Playwright-compatible selectors like: role=button[name=\"...\"] (not separate arguments).
4. Define reusable keywords for actions like opening the browser, accepting cookies, navigating, etc.
5. Use variables like ${BASE_URL} and ${BROWSER_TYPE} to make the script reusable.
6. For video recording, always use `New Context    recordVideo={'dir': './execution_videos/<script_name>'}` when creating a new browser context, where <script_name> is the name of the test script. This ensures each test script's video is stored in its own folder.
7. When closing, use `Close Context` instead of `Close Browser` to ensure video is saved.
8. Do NOT use [exact=true] in any locator or command. All selectors should be written without the [exact=true] option.
9. Output only the Robot Framework code block. Do not add explanations or comments outside the code.
10. Ensure the code is directly runnable using `robot` CLI.

Respond only with a valid JSON object in the following format:
{
  "robot_code": "<Robot Framework code here>"
}
"""

    def _build_user_prompt(self, playwright_script, project_metadata=None):
        """Build the user prompt with context"""
        prompt = f"""Convert the following Playwright Python script to Robot Framework Browser Library format:

PLAYWRIGHT SCRIPT:
```python
{playwright_script}
```

Please follow all the conversion rules and best practices outlined in the system prompt.
Create a comprehensive Robot Framework test that is maintainable and follows industry standards.
"""

        if project_metadata:
            prompt += f"\nPROJECT CONTEXT:\n{project_metadata}\n"
        
        return prompt
    
    def _enhance_robot_script(self, robot_script, project_metadata=None):
        """Enhance and validate the generated Robot Framework script"""
        # Basic validation and enhancement logic
        lines = robot_script.split('\n')
        
        # Ensure proper sections exist
        required_sections = ['*** Settings ***', '*** Test Cases ***']
        for section in required_sections:
            if not any(section in line for line in lines):
                logger.warning(f"Missing required section: {section}")
        
        # Add basic structure if missing
        if '*** Settings ***' not in robot_script:
            robot_script = "*** Settings ***\nLibrary    Browser\n\n" + robot_script
        
        return robot_script
