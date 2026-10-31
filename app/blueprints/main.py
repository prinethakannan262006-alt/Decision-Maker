import time
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, jsonify, abort, current_app
from app.models import db, FAQ, ErrorCode, SupportTicket, Decision
from app.services.weather_service import get_weather_decision

main_bp = Blueprint("main", __name__)

@main_bp.route("/")
def index():
    """Home landing page."""
    faq_count = FAQ.query.count()
    saved_decisions_count = Decision.query.count()
    return render_template(
        "index.html",
        faq_count=faq_count,
        saved_decisions_count=saved_decisions_count
    )

@main_bp.route("/decision-tool")
def decision_tool():
    """Interactive Decision Tool page with Weighted Matrix and Quick Picks."""
    recent_decisions = Decision.query.order_by(Decision.created_at.desc()).limit(5).all()
    weather_data = get_weather_decision()
    return render_template(
        "decision_tool.html",
        recent_decisions=recent_decisions,
        weather=weather_data
    )

@main_bp.route("/faqs")
def faqs():
    """FAQs page populated dynamically from SQL database."""
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    query = FAQ.query
    if category:
        query = query.filter_by(category=category)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((FAQ.question.ilike(search_filter)) | (FAQ.answer.ilike(search_filter)))

    all_faqs = query.all()
    # Get distinct categories
    categories = [cat[0] for cat in db.session.query(FAQ.category).distinct().all()]

    return render_template(
        "faqs.html",
        faqs=all_faqs,
        categories=categories,
        selected_category=category,
        search_query=search
    )

@main_bp.route("/error-codes")
def error_codes():
    """Error codes and troubleshooting table."""
    codes = ErrorCode.query.order_by(ErrorCode.code).all()
    return render_template("error_codes.html", error_codes=codes)

@main_bp.route("/support", methods=["GET", "POST"])
def support():
    """Manual support ticket creation and status lookup."""
    ticket_result = None
    lookup_result = None
    error_message = None

    if request.method == "POST":
        action = request.form.get("action")
        if action == "create":
            user_message = request.form.get("user_message", "").strip()
            email = request.form.get("email", "").strip() or None
            if not user_message:
                error_message = "Please describe your question or issue."
            else:
                ticket = SupportTicket(user_message=user_message, email=email)
                db.session.add(ticket)
                db.session.commit()
                ticket_result = ticket
        elif action == "lookup":
            ticket_id = request.form.get("ticket_id", "").strip()
            if not ticket_id:
                error_message = "Please enter a valid Ticket ID."
            else:
                lookup_result = SupportTicket.query.filter_by(id=ticket_id).first()
                if not lookup_result:
                    error_message = f"No ticket found with ID: {ticket_id}"

    return render_template(
        "support.html",
        ticket_result=ticket_result,
        lookup_result=lookup_result,
        error_message=error_message
    )

@main_bp.route("/admin/tickets")
def admin_tickets():
    """
    Protected admin view for tickets.
    Triggers 401 Unauthorized if token is missing.
    Triggers 403 Forbidden if token is invalid.
    """
    admin_token_config = current_app.config.get("ADMIN_TOKEN", "dm-admin-secret-token")
    auth_header = request.headers.get("Authorization", "")
    token_param = request.args.get("token", "")

    provided_token = ""
    if auth_header.startswith("Bearer "):
        provided_token = auth_header.split(" ", 1)[1].strip()
    elif token_param:
        provided_token = token_param.strip()

    if not provided_token:
        # Trigger 401 Unauthorized
        abort(401)

    if provided_token != admin_token_config:
        # Trigger 403 Forbidden
        abort(403)

    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return render_template("admin_tickets.html", tickets=tickets)

@main_bp.route("/health")
def health():
    """
    Health check monitoring endpoint.
    Content-negotiates HTML dashboard or JSON response.
    Returns HTTP 503 if core SQL dependency is down.
    """
    # 1. SQL database check
    sql_healthy = False
    try:
        db.session.execute(db.text("SELECT 1"))
        sql_healthy = True
    except Exception:
        sql_healthy = False

    # 2. MongoDB Atlas check
    mongo_healthy = False
    mongo_service = getattr(current_app, "mongo_service", None)
    if mongo_service:
        mongo_healthy = mongo_service.is_connected()

    # 3. Third-party API check
    weather_data = get_weather_decision()
    api_healthy = weather_data.get("status") == "live"

    # Uptime calculation
    start_time = getattr(current_app, "start_time", time.time())
    uptime_seconds = int(time.time() - start_time)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_formatted = f"{hours}h {minutes}m {seconds}s"

    overall_status = "HEALTHY" if sql_healthy else "UNHEALTHY"
    http_status = 200 if sql_healthy else 503

    report = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": uptime_formatted,
        "uptime_seconds": uptime_seconds,
        "dependencies": {
            "sql_database": {
                "status": "UP" if sql_healthy else "DOWN",
                "type": "PostgreSQL" if "postgresql" in current_app.config.get("SQLALCHEMY_DATABASE_URI", "") else "SQLite"
            },
            "mongodb_atlas": {
                "status": "UP" if mongo_healthy else "OFFLINE_FALLBACK",
                "notes": "Non-blocking analytics & chat logs"
            },
            "third_party_weather_api": {
                "status": "UP" if api_healthy else "FALLBACK",
                "source": weather_data.get("source")
            }
        }
    }

    # Respond in JSON if requested via header or query param
    if request.is_json or request.args.get("format") == "json" or request.headers.get("Accept") == "application/json":
        return jsonify(report), http_status

    return render_template("health.html", report=report, http_status=http_status), http_status

# Error simulation routes to explicitly demonstrate every status code
@main_bp.route("/trigger-error/<code_name>")
def trigger_error(code_name):
    """Explicitly triggers error status codes for demonstration and testing."""
    code_name = code_name.upper()
    if code_name == "400":
        abort(400)
    elif code_name == "401":
        abort(401)
    elif code_name == "403":
        abort(403)
    elif code_name == "404":
        abort(404)
    elif code_name == "429":
        abort(429)
    elif code_name == "500":
        abort(500)
    elif code_name == "503":
        abort(503)
    elif code_name == "DM-901":
        # Custom application error code
        abort(400, description="DM-901: Decision input invalid. Please provide at least 2 options and 1 weighted criterion.")
    else:
        abort(404)
