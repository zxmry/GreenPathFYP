"""GreenPath Flask application factory."""

from flask import Flask
import os
import config


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )
    app.secret_key = config.SECRET_KEY

    # Ensure static folder exists
    static_path = os.path.join(os.path.dirname(__file__), "..", "static")
    if not os.path.exists(static_path):
        os.makedirs(static_path)

    # Register blueprints
    from app.auth import auth_bp
    from app.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    return app

