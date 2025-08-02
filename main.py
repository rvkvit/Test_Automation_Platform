import os
import logging
from app import create_app

# Configure logging for better debugging
logging.basicConfig(level=logging.DEBUG)

if __name__ == '__main__':
    try:
        app = create_app()

        port = int(os.environ.get('PORT', 5000))
        host = '0.0.0.0'

        print(f"Starting TestCraft Pro on {host}:{port}")
        app.run(host=host, port=port, debug=True)
    except Exception as e:
        print(f"Failed to start application: {e}")
        import traceback
        traceback.print_exc()