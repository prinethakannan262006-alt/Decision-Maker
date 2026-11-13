import json
import time
import random
from datetime import datetime, timezone
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.exceptions import PermissionDenied

from core.models import FAQ, ErrorCode, SupportTicket, Decision
from core.services.ai_service import process_chat_message
from core.services.mongo_service import mongo_service
from core.services.weather_service import get_weather_decision

# Start timestamp for uptime tracking
START_TIME = time.time()

# ==========================================
# WEB PAGE VIEWS
# ==========================================

def index(request):
    """Home landing page."""
    faq_count = FAQ.objects.count()
    saved_decisions_count = Decision.objects.count()
    return render(request, "index.html", {
        "faq_count": faq_count,
        "saved_decisions_count": saved_decisions_count
    })

def decision_tool(request):
    """Decision Matrix and Quick Picks page."""
    recent_decisions = Decision.objects.order_by("-created_at")[:5]
    weather_data = get_weather_decision()
    return render(request, "decision_tool.html", {
        "recent_decisions": recent_decisions,
        "weather": weather_data
    })

def faqs(request):
    """Knowledge base FAQs queried dynamically from SQL database."""
    category = request.GET.get("category", "").strip()
    search = request.GET.get("search", "").strip()

    qs = FAQ.objects.all()
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(question__icontains=search) | qs.filter(answer__icontains=search)

    categories = list(FAQ.objects.values_list("category", flat=True).distinct())

    return render(request, "faqs.html", {
        "faqs": qs,
        "categories": categories,
        "selected_category": category,
        "search_query": search
    })

def error_codes(request):
    """Status & Error Codes reference table from SQL database."""
    codes = ErrorCode.objects.order_by("code")
    return render(request, "error_codes.html", {
        "error_codes": codes
    })

def support(request):
    """Manual support ticket creation and status lookup."""
    ticket_result = None
    lookup_result = None
    error_message = None

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            user_message = request.POST.get("user_message", "").strip()
            email = request.POST.get("email", "").strip() or None
            if not user_message:
                error_message = "Please describe your question or issue."
            else:
                ticket_result = SupportTicket.objects.create(
                    user_message=user_message,
                    email=email
                )
        elif action == "lookup":
            ticket_id = request.POST.get("ticket_id", "").strip()
            if not ticket_id:
                error_message = "Please enter a valid Ticket ID."
            else:
                lookup_result = SupportTicket.objects.filter(id=ticket_id).first()
                if not lookup_result:
                    error_message = f"No ticket found with ID: {ticket_id}"

    return render(request, "support.html", {
        "ticket_result": ticket_result,
        "lookup_result": lookup_result,
        "error_message": error_message
    })

def admin_tickets(request):
    """
    Protected admin view for support tickets.
    401 Unauthorized if token is missing.
    403 Forbidden if token is invalid.
    """
    admin_token_config = getattr(settings, "ADMIN_TOKEN", "dm-admin-secret-token")
    auth_header = request.headers.get("Authorization", "")
    token_param = request.GET.get("token", "")

    provided_token = ""
    if auth_header.startswith("Bearer "):
        provided_token = auth_header.split(" ", 1)[1].strip()
    elif token_param:
        provided_token = token_param.strip()

    if not provided_token:
        return custom_unauthorized_401(request)

    if provided_token != admin_token_config:
        return custom_permission_denied_403(request)

    tickets = SupportTicket.objects.order_by("-created_at")
    return render(request, "admin_tickets.html", {
        "tickets": tickets
    })

def health_view(request):
    """
    Live system status and health check endpoint.
    Content-negotiates HTML dashboard or JSON response.
    Returns HTTP 503 if core SQL dependency is down.
    """
    # 1. SQL Database check
    sql_healthy = False
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        sql_healthy = True
    except Exception:
        sql_healthy = False

    # 2. MongoDB Atlas check
    mongo_healthy = mongo_service.is_connected()

    # 3. Third-party API check
    weather_data = get_weather_decision()
    api_healthy = weather_data.get("status") == "live"

    uptime_seconds = int(time.time() - START_TIME)
    hours, rem = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    uptime_formatted = f"{hours}h {minutes}m {seconds}s"

    overall_status = "HEALTHY" if sql_healthy else "UNHEALTHY"
    http_status = 200 if sql_healthy else 503

    db_engine = settings.DATABASES["default"]["ENGINE"]
    db_type = "PostgreSQL" if "postgresql" in db_engine else "SQLite"

    report = {
        "status": overall_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "uptime": uptime_formatted,
        "uptime_seconds": uptime_seconds,
        "dependencies": {
            "sql_database": {
                "status": "UP" if sql_healthy else "DOWN",
                "type": db_type
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

    if request.GET.get("format") == "json" or request.headers.get("Accept") == "application/json":
        return JsonResponse(report, status=http_status)

    return render(request, "health.html", {
        "report": report,
        "http_status": http_status
    }, status=http_status)

def trigger_error_view(request, code_name):
    """Explicitly triggers error status codes for demonstration and testing."""
    code = code_name.upper()
    if code == "400":
        return custom_bad_request_400(request, description="Bad Request triggered for testing.")
    elif code == "401":
        return custom_unauthorized_401(request)
    elif code == "403":
        return custom_permission_denied_403(request)
    elif code == "404":
        return custom_page_not_found_404(request)
    elif code == "429":
        return custom_ratelimit_429(request)
    elif code == "500":
        return custom_server_error_500(request)
    elif code == "503":
        return custom_service_unavailable_503(request)
    elif code == "DM-901":
        return custom_bad_request_400(
            request,
            description="DM-901: Decision input invalid. Please provide at least 2 options and 1 weighted criterion."
        )
    return custom_page_not_found_404(request)

# ==========================================
# REST API ENDPOINTS
# ==========================================

@csrf_exempt
def api_matrix_calculate(request):
    """Calculates weighted decision matrix scores. Returns DM-901 if invalid."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    options = data.get("options", [])
    criteria = data.get("criteria", [])
    scores = data.get("scores", {})

    if not isinstance(options, list) or len(options) < 2:
        return JsonResponse({
            "error_code": "DM-901",
            "error": "Decision input invalid: At least two options are required to make a comparison.",
            "suggested_fix": "Add at least two distinct options (e.g. 'Option A', 'Option B')."
        }, status=400)

    if not isinstance(criteria, list) or len(criteria) < 1:
        return JsonResponse({
            "error_code": "DM-901",
            "error": "Decision input invalid: At least one criterion with weight is required.",
            "suggested_fix": "Add at least one criterion with a weight between 1 and 5."
        }, status=400)

    results = []
    total_weights = sum(float(c.get("weight", 1)) for c in criteria)
    if total_weights <= 0:
        total_weights = 1.0

    for option in options:
        opt_name = str(option).strip()
        opt_scores = scores.get(opt_name, {})
        weighted_sum = 0.0
        breakdown = []

        for crit in criteria:
            crit_name = str(crit.get("name", "")).strip()
            crit_weight = float(crit.get("weight", 1))
            crit_weight = max(1.0, min(5.0, crit_weight))
            
            raw_score = float(opt_scores.get(crit_name, 5))
            raw_score = max(1.0, min(10.0, raw_score))
            
            weighted_contrib = raw_score * crit_weight
            weighted_sum += weighted_contrib

            breakdown.append({
                "criterion": crit_name,
                "weight": crit_weight,
                "raw_score": raw_score,
                "weighted_contrib": round(weighted_contrib, 2)
            })

        results.append({
            "option": opt_name,
            "total_score": round(weighted_sum, 2),
            "normalized_score": round((weighted_sum / (total_weights * 10)) * 100, 1),
            "breakdown": breakdown
        })

    results.sort(key=lambda x: x["total_score"], reverse=True)
    winner = results[0]["option"] if results else "None"

    return JsonResponse({
        "status": "success",
        "winner": winner,
        "winner_score": results[0]["total_score"] if results else 0,
        "results": results
    })

@csrf_exempt
def api_matrix_save(request):
    """Saves a completed matrix decision into SQL database."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    title = data.get("title", "My Weighted Decision").strip() or "Untitled Decision"
    options = data.get("options", [])
    criteria = data.get("criteria", [])
    scores = data.get("scores", {})
    winner = data.get("winner", "Unknown")
    total_score = float(data.get("total_score", 0.0))

    if not options or not criteria:
        return JsonResponse({
            "error_code": "DM-901",
            "error": "Cannot save empty or invalid decision evaluation."
        }, status=400)

    decision = Decision.objects.create(
        title=title,
        options=json.dumps(options),
        criteria=json.dumps(criteria),
        scores=json.dumps(scores),
        winner=winner,
        total_score=total_score
    )

    return JsonResponse({
        "status": "success",
        "id": decision.id,
        "message": f"Decision '{title}' saved successfully to database!",
        "decision": decision.to_dict()
    }, status=201)

def api_decisions(request):
    """Fetches recently saved decisions from SQL database."""
    decisions = Decision.objects.order_by("-created_at")[:20]
    return JsonResponse({
        "count": len(decisions),
        "decisions": [d.to_dict() for d in decisions]
    })

@csrf_exempt
def api_chat(request):
    """AI Assistant chat endpoint. Connects to FAQ/Error lookup and MongoDB Atlas."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default_session").strip()

    if not message:
        return JsonResponse({"error": "Message is required."}, status=400)

    result = process_chat_message(message)

    mongo_service.log_chat(
        session_id=session_id,
        user_message=message,
        bot_reply=result["reply"],
        matched_source=result["source"]
    )

    return JsonResponse({
        "reply": result["reply"],
        "source": result["source"],
        "ticket_id": result.get("ticket_id")
    })

@csrf_exempt
def api_feedback(request):
    """Logs thumbs-up / thumbs-down rating to MongoDB Atlas."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    session_id = data.get("session_id", "unknown")
    message_id = data.get("message_id", "msg-1")
    rating = data.get("rating", 1)
    comment = data.get("comment", "")

    logged = mongo_service.log_feedback(
        session_id=session_id,
        message_id=message_id,
        rating=rating,
        comment=comment
    )

    return JsonResponse({
        "status": "success",
        "saved_to_mongo": logged,
        "message": "Thank you for your feedback!"
    })

def api_quick_picks_coin(request):
    """Simulates a random coin flip."""
    outcome = "Heads" if random.random() < 0.5 else "Tails"
    return JsonResponse({
        "tool": "Coin Flip",
        "result": outcome,
        "icon": "🪙",
        "explanation": f"The coin landed on {outcome}."
    })

def api_quick_picks_dice(request):
    """Simulates dice roll."""
    try:
        sides = int(request.GET.get("sides", 6))
    except ValueError:
        sides = 6
    if sides < 2 or sides > 100:
        sides = 6
    value = random.randint(1, sides)
    return JsonResponse({
        "tool": "Dice Roll",
        "sides": sides,
        "result": value,
        "icon": "🎲",
        "explanation": f"Rolled a {value} on a {sides}-sided die."
    })

@csrf_exempt
def api_quick_picks_random(request):
    """Picks a random item from user-submitted list."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    items = data.get("items", [])
    if not isinstance(items, list) or len(items) < 2:
        return JsonResponse({
            "error_code": "DM-901",
            "error": "Please provide at least 2 items to pick from."
        }, status=400)

    clean_items = [str(item).strip() for item in items if str(item).strip()]
    if len(clean_items) < 2:
        return JsonResponse({
            "error_code": "DM-901",
            "error": "Please provide at least 2 non-empty items."
        }, status=400)

    choice = random.choice(clean_items)
    return JsonResponse({
        "tool": "Random Pick",
        "result": choice,
        "candidates": clean_items,
        "icon": "🎯",
        "explanation": f"Selected '{choice}' out of {len(clean_items)} candidates."
    })

def api_weather(request):
    """Returns weather decision from Open-Meteo with fallback."""
    decision = get_weather_decision()
    return JsonResponse(decision)

def api_faqs(request):
    """Returns all FAQs from SQL database via API."""
    category = request.GET.get("category", "").strip()
    search = request.GET.get("search", "").strip()

    qs = FAQ.objects.all()
    if category:
        qs = qs.filter(category=category)
    if search:
        qs = qs.filter(question__icontains=search) | qs.filter(answer__icontains=search)

    return JsonResponse({
        "status": "success",
        "count": qs.count(),
        "faqs": [f.to_dict() for f in qs]
    })

def api_error_codes(request):
    """Returns all error codes from SQL database via API."""
    codes = ErrorCode.objects.order_by("code")
    return JsonResponse({
        "status": "success",
        "count": codes.count(),
        "error_codes": [c.to_dict() for c in codes]
    })

def api_tickets_list(request):
    """CRUD (Read all): Returns all support tickets."""
    tickets = SupportTicket.objects.order_by("-created_at")
    return JsonResponse({
        "status": "success",
        "count": tickets.count(),
        "tickets": [t.to_dict() for t in tickets]
    })

@csrf_exempt
def api_ticket_create(request):
    """CRUD (Create): API endpoint to create a support ticket."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except Exception:
        data = {}

    message = data.get("user_message", "").strip()
    email = data.get("email", "").strip() or None

    if not message:
        return JsonResponse({"error": "Support ticket message cannot be empty."}, status=400)

    ticket = SupportTicket.objects.create(user_message=message, email=email)
    return JsonResponse({
        "status": "success",
        "ticket": ticket.to_dict()
    }, status=201)

@csrf_exempt
def api_ticket_detail(request, ticket_id):
    """
    CRUD (Read, Update, Delete) on single ticket:
    - GET: retrieve ticket
    - PUT: update ticket
    - DELETE: delete ticket
    """
    ticket = SupportTicket.objects.filter(id=ticket_id).first()
    if not ticket:
        return JsonResponse({"error": f"Ticket '{ticket_id}' not found."}, status=404)

    if request.method == "GET":
        return JsonResponse(ticket.to_dict())

    elif request.method == "PUT":
        try:
            data = json.loads(request.body.decode("utf-8")) if request.body else {}
        except Exception:
            data = {}

        if "status" in data:
            ticket.status = str(data["status"]).strip()
        if "email" in data:
            ticket.email = str(data["email"]).strip() or None
        if "user_message" in data:
            ticket.user_message = str(data["user_message"]).strip()
        ticket.save()

        return JsonResponse({
            "status": "success",
            "message": f"Ticket '{ticket_id}' updated successfully.",
            "ticket": ticket.to_dict()
        })

    elif request.method == "DELETE":
        ticket.delete()
        return JsonResponse({
            "status": "success",
            "message": f"Ticket '{ticket_id}' deleted successfully."
        })

    return JsonResponse({"error": "Method not allowed"}, status=405)

def api_trigger_rate_limit(request):
    """Test endpoint for rate limit demonstration."""
    return JsonResponse({
        "status": "ok",
        "message": "Rate limit demonstration endpoint."
    })

# ==========================================
# CUSTOM ERROR HANDLERS (HTML & JSON)
# ==========================================

def _render_error_response(request, status_code, title, description):
    """Unified handler: returns JSON for /api/*, HTML for web pages."""
    if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
        return JsonResponse({
            "error_code": str(status_code),
            "title": title,
            "description": description,
            "path": request.path
        }, status=status_code)

    template_name = f"errors/{status_code}.html"
    return render(request, template_name, {
        "status_code": status_code,
        "title": title,
        "description": description
    }, status=status_code)

def custom_bad_request_400(request, exception=None, description="The request syntax was invalid or missing required parameters."):
    return _render_error_response(request, 400, "Bad Request", description)

def custom_unauthorized_401(request, exception=None):
    return _render_error_response(request, 401, "Unauthorized", "Authentication credentials are required to view this protected resource.")

def custom_permission_denied_403(request, exception=None):
    return _render_error_response(request, 403, "Forbidden", "You do not have permission to access this administrative section.")

def custom_page_not_found_404(request, exception=None):
    return _render_error_response(request, 404, "Page Not Found", "The requested page or resource could not be found.")

def custom_ratelimit_429(request, exception=None):
    return _render_error_response(request, 429, "Too Many Requests", "You have exceeded the allowed rate limit. Please wait a minute and try again.")

def custom_server_error_500(request):
    return _render_error_response(request, 500, "Internal Server Error", "An unexpected condition was encountered on the server.")

def custom_service_unavailable_503(request, exception=None):
    return _render_error_response(request, 503, "Service Unavailable", "The service is temporarily unavailable or undergoing maintenance.")
