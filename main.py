import os
import logging
from app import create_app

# Configure logging for better debugging
logging.basicConfig(level=logging.DEBUG)

app = create_app()

if __name__ == '__main__':
    # Get port from environment or default to 5000
    port = int(os.environ.get('PORT', 5000))
    # Set debug mode based on FLASK_DEBUG env var (default: False)
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1'
    # Bind to 0.0.0.0 for external access
    app.run(host='0.0.0.0', port=port, debug=debug_mode)
