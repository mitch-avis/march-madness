import logging
from logging.config import dictConfig

from flask import Flask
from flask_cors import CORS

from src.config.env_config import Config
from src.config.logger_config import LOGGING_CONFIG

# Logger formatting
dictConfig(LOGGING_CONFIG)
# Create logger
log = logging.getLogger(__name__)


def create_app(config_class=Config):
    """Creates the Flask application."""
    # Create Flask app
    app = Flask(__name__)
    # Load flask config
    app.config.from_object(config_class)
    # Configure CORS
    allowed_origins = config_class.ALLOWED_ORIGINS
    CORS(app, origins=allowed_origins)
    # Finish app initialization
    with app.app_context():
        # Add Flask Blueprints to app
        _add_blueprints(app)
        # Return initialized app
        return app


def _add_blueprints(app: Flask):
    """Registers Flask Blueprints."""
    from src.api.views import api_bp
    from src.errors.views import errors_bp

    # Add error handlers blueprint to app
    app.register_blueprint(errors_bp)
    # Add API endpoints blueprint to app
    app.register_blueprint(api_bp, url_prefix="/")
