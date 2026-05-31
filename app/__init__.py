"""GreenPath Flask application factory — SQLite version."""

import os
import config
from flask import Flask


def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(__file__), "..", "static"),
        template_folder=os.path.join(os.path.dirname(__file__), "..", "templates"),
    )
    app.secret_key = config.SECRET_KEY

    # Initialise the SQLite database (creates tables if not exist)
    from app.database import init_db
    init_db()

    # Ensure static folder exists
    static_path = os.path.join(os.path.dirname(__file__), "..", "static")
    if not os.path.exists(static_path):
        os.makedirs(static_path)

    from app.auth import auth_bp
    from app.api import api_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    return app
