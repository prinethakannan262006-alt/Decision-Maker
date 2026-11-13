import os
import time
import logging
from logging.handlers import RotatingFileHandler
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.core.cache import cache

logger = logging.getLogger("request_logger")

class RequestLoggingMiddleware:
    """
    Middleware that records:
    - HTTP method
    - Request path
    - Response status
    - Request duration in milliseconds
    - Client IP address
    Logs to console and rotating log file (logs/app.log).
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self._setup_logger()

    def _setup_logger(self):
        logs_dir = os.path.join(settings.BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)
        log_file = os.path.join(logs_dir, "app.log")

        formatter = logging.Formatter(
            "[%(asctime)s] %(levelname)s: %(message)s"
        )

        # Rotating file handler: 5MB per file, keeping 5 backup logs
        file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=5)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        logger.handlers.clear()
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        logger.setLevel(logging.INFO)

    def __call__(self, request):
        start_time = time.time()
        response = self.get_response(request)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        # Don't clutter logs with static file requests
        if not request.path.startswith("/static"):
            ip = request.META.get("HTTP_X_FORWARDED_FOR")
            if ip:
                ip = ip.split(",")[0].strip()
            else:
                ip = request.META.get("REMOTE_ADDR", "127.0.0.1")

            # Structured, safe log entry (never logging passwords or sensitive payloads)
            logger.info(
                f"{request.method} {request.path} -> {response.status_code} "
                f"({duration_ms}ms) [IP: {ip}]"
            )

        return response
