import logging
import os
from dotenv import load_dotenv

from web import create_app

load_dotenv()
app = create_app()

if __name__ != '__main__':
    # Use gunicorn logging
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

if __name__ == '__main__':
    is_debug = os.environ.get("DEBUG", "False").lower() == "true"
    port = int(os.environ.get('PORT', 5000))

    app.run(debug=is_debug, host="0.0.0.0", port=port)
