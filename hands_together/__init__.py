"""Application factory and configuration for Hands Together."""

import os

from flask import Flask

from .models import init_db


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="../static",
        template_folder="../templates",
        static_url_path="",
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "HANDS_TOGETHER_SECRET", "local-development-key-change-before-deployment"
        ),
        DATABASE=os.path.join(app.instance_path, "hands_together.db"),
        ADMIN_REGISTRATION_PASS=os.environ.get("HANDS_TOGETHER_ADMIN_PASS", "We Shall Overcome"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    if test_config is not None:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from .routes import web

    app.register_blueprint(web)
    with app.app_context():
        init_db()

    return app
