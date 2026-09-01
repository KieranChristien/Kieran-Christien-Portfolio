import cloudinary
import os
from dotenv import load_dotenv
from flask import Flask
from flask_bootstrap import Bootstrap
from flask_migrate import upgrade

from web.errors import register_error_handlers
from web.extensions import db, limiter, login_manager, migrate
from web.forms import AddProjectForm, ContactForm, EditProjectForm, LoginAdminForm, RegisterAdminForm
from web.models import ensure_owner


def create_app():
    load_dotenv()
    env = os.environ

    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = env.get('SECRET_KEY')
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

    database_url = env.get('DB_URI')
    if not database_url:
        raise RuntimeError("DATABASE_URI is not configured")

    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config["OWNER_NAME"] = env.get("OWNER_NAME")
    app.config["OWNER_EMAIL"] = env.get("OWNER_EMAIL")
    app.config["OWNER_PASSWORD"] = env.get("OWNER_PASSWORD")

    app.config['RATELIMIT_STORAGE_URI'] = env.get(
        "STORAGE_URI",
        "memory://"
    )

    # Extensions
    Bootstrap(app)
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    login_manager.init_app(app)

    # Flask-Login configuration
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."

    # Cloudinary configuration
    cloudinary.config(
        cloud_name=env.get("CLOUDINARY_NAME"),
        api_key=env.get("CLOUDINARY_KEY"),
        api_secret=env.get("CLOUDINARY_SECRET"),
        secure=True,
    )

    # Register blueprints
    from web.routes.main import main
    from web.routes.auth import auth
    from web.routes.projects import projects

    app.register_blueprint(main)
    app.register_blueprint(auth)
    app.register_blueprint(projects)

    # Application services
    register_error_handlers(app)

    # Ensure owner account exists
    with app.app_context():
        upgrade()
        ensure_owner()

    return app
