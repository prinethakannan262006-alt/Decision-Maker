import os
import time
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, request, jsonify, render_template, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from app.config import Config, DevelopmentConfig, ProductionConfig
from app.models import db
from app.services.db_service import seed_database_safely
from app.services.mongo_service import MongoService

# Global limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120 per minute"]
)

def setup_logging(app):
    """Configures console and rotating file logger without logging sensitive data."""
    logs_dir = os.path.join(app.root_path, "..", "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, "app.log")

    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s"
    )

    # Rotating file handler: 5MB per file, keeping 5 backup logs
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    # Console stream handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)

    # Close and remove existing handlers to avoid unclosed file ResourceWarnings
    for handler in list(app.logger.handlers):
        try:
            handler.close()
        except Exception:
            pass
        app.logger.removeHandler(handler)
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.INFO)

    # Request logging middleware
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        # Exclude static assets from spamming logs
        if not request.path.startswith("/static"):
            duration = round((time.time() - getattr(g, "start_time", time.time())) * 1000, 2)
            ip_address = request.headers.get("X-Forwarded-For", request.remote_addr)
            # Log method, path, status, duration, IP (no passwords or body secrets)
            app.logger.info(
                f"{request.method} {request.path} -> {response.status_code} "
                f"({duration}ms) [IP: {ip_address}]"
            )
        return response

def register_error_handlers(app):
    """Registers unified error handlers for HTML and JSON API responses."""
    
    def handle_error(status_code, default_title, default_desc):
        # Check if request is for API or expects JSON
        if request.path.startswith("/api/") or request.is_json or request.headers.get("Accept") == "application/json":
            return jsonify({
                "error_code": str(status_code),
                "title": default_title,
                "description": default_desc,
                "path": request.path
            }), status_code
        
        # Render dedicated custom error template matching website design
        template_name = f"errors/{status_code}.html"
        return render_template(
            template_name,
            status_code=status_code,
            title=default_title,
            description=default_desc
        ), status_code

    @app.errorhandler(400)
    def bad_request(e):
        desc = getattr(e, "description", "The request syntax was invalid or missing required parameters.")
        return handle_error(400, "Bad Request", desc)

    @app.errorhandler(401)
    def unauthorized(e):
        return handle_error(401, "Unauthorized", "Authentication credentials are required to view this protected resource.")

    @app.errorhandler(403)
    def forbidden(e):
        return handle_error(403, "Forbidden", "You do not have permission to access this administrative section.")

    @app.errorhandler(404)
    def not_found(e):
        return handle_error(404, "Page Not Found", "The requested page or resource could not be found.")

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return handle_error(429, "Too Many Requests", "You have exceeded the allowed rate limit. Please wait a minute and try again.")

    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f"Internal Server Error: {e}")
        return handle_error(500, "Internal Server Error", "An unexpected condition was encountered on the server.")

    @app.errorhandler(503)
    def service_unavailable(e):
        return handle_error(503, "Service Unavailable", "The service is temporarily unavailable or undergoing maintenance.")

def create_app(config_class=None):
    """Application factory for Decision Maker."""
    app = Flask(__name__)

    if config_class is None:
        env = os.getenv("FLASK_ENV", "production")
        config_class = DevelopmentConfig if env == "development" else ProductionConfig

    app.config.from_object(config_class)

    # Record application start timestamp for uptime tracking
    app.start_time = time.time()

    # Configure logging
    setup_logging(app)

    # Initialize SQL database
    db.init_app(app)

    # Initialize rate limiter
    limiter.init_app(app)
    app.limiter = limiter

    # Initialize MongoDB Atlas service
    mongo_uri = app.config.get("MONGO_URI", "")
    mongo_db_name = app.config.get("MONGO_DB_NAME", "decision_maker")
    app.mongo_service = MongoService(uri=mongo_uri, db_name=mongo_db_name)

    # Register Blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.api import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)

    # Apply specific rate limits to sensitive API routes
    try:
        limiter.limit("45 per minute")(api_bp)
    except Exception:
        pass

    # Register error handlers
    register_error_handlers(app)

    # Create tables and safely seed database without duplicating records
    with app.app_context():
        try:
            # Ensure SQLite instance dir exists if local
            if "sqlite:///" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
                instance_dir = os.path.join(app.root_path, "..", "instance")
                os.makedirs(instance_dir, exist_ok=True)
            db.create_all()
            seed_database_safely()
            app.logger.info("Database schema initialized and seed data verified.")
        except Exception as e:
            app.logger.error(f"Database initialization error: {e}")

    return app
