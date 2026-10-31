import json
import random
from flask import Blueprint, request, jsonify, current_app
from app.models import db, Decision, SupportTicket, FAQ, ErrorCode
from app.services.ai_service import process_chat_message
from app.services.weather_service import get_weather_decision

api_bp = Blueprint("api", __name__, url_prefix="/api")

@api_bp.route("/matrix/calculate", methods=["POST"])
def calculate_matrix():
    """
    Calculates weighted decision matrix scores.
    Validates criteria, weights, and options.
    Returns DM-901 error code if validation fails.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            "error_code": "DM-901",
            "error": "Decision input invalid: Missing JSON payload.",
            "suggested_fix": "Provide valid JSON with options, criteria, and scores."
        }), 400

    options = data.get("options", [])
    criteria = data.get("criteria", [])
    scores = data.get("scores", {})

    # Validation: at least 2 options, at least 1 criterion
    if not isinstance(options, list) or len(options) < 2:
        return jsonify({
            "error_code": "DM-901",
            "error": "Decision input invalid: At least two options are required to make a comparison.",
            "suggested_fix": "Add at least two distinct options (e.g. 'Option A', 'Option B')."
        }), 400

    if not isinstance(criteria, list) or len(criteria) < 1:
        return jsonify({
            "error_code": "DM-901",
            "error": "Decision input invalid: At least one criterion with weight is required.",
            "suggested_fix": "Add at least one criterion with a weight between 1 and 5."
        }), 400

    # Calculate weighted scores
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
            # Bound weight between 1 and 5
            crit_weight = max(1.0, min(5.0, crit_weight))
            
            # Score default 5 if not provided, bounded 1 to 10
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

    # Sort descending by total score
    results.sort(key=lambda x: x["total_score"], reverse=True)
    winner = results[0]["option"] if results else "None"

    return jsonify({
        "status": "success",
        "winner": winner,
        "winner_score": results[0]["total_score"] if results else 0,
        "results": results
    })

@api_bp.route("/matrix/save", methods=["POST"])
def save_matrix():
    """Saves a completed matrix decision into SQL database."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "My Weighted Decision").strip() or "Untitled Decision"
    options = data.get("options", [])
    criteria = data.get("criteria", [])
    scores = data.get("scores", {})
    winner = data.get("winner", "Unknown")
    total_score = float(data.get("total_score", 0.0))

    if not options or not criteria:
        return jsonify({
            "error_code": "DM-901",
            "error": "Cannot save empty or invalid decision evaluation."
        }), 400

    decision = Decision(
        title=title,
        options=json.dumps(options),
        criteria=json.dumps(criteria),
        scores=json.dumps(scores),
        winner=winner,
        total_score=total_score
    )
    db.session.add(decision)
    db.session.commit()

    return jsonify({
        "status": "success",
        "id": decision.id,
        "message": f"Decision '{title}' saved successfully to database!",
        "decision": decision.to_dict()
    }), 201

@api_bp.route("/decisions", methods=["GET"])
def get_decisions():
    """Fetches recently saved decisions from SQL database."""
    decisions = Decision.query.order_by(Decision.created_at.desc()).limit(20).all()
    return jsonify({
        "count": len(decisions),
        "decisions": [d.to_dict() for d in decisions]
    })

@api_bp.route("/chat", methods=["POST"])
def chat():
    """
    AI Assistant chat endpoint.
    Processes error codes, FAQ grounding, LLM generation,
    and automatic ticket creation fallback.
    Logs interaction to MongoDB Atlas.
    """
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "default_session").strip()

    if not message:
        return jsonify({"error": "Message is required."}), 400

    # Process through pipeline
    result = process_chat_message(message, current_app.config)

    # Log to MongoDB Atlas
    mongo_service = getattr(current_app, "mongo_service", None)
    if mongo_service:
        mongo_service.log_chat(
            session_id=session_id,
            user_message=message,
            bot_reply=result["reply"],
            matched_source=result["source"]
        )

    return jsonify({
        "reply": result["reply"],
        "source": result["source"],
        "ticket_id": result.get("ticket_id")
    })

@api_bp.route("/feedback", methods=["POST"])
def feedback():
    """
    Logs thumbs-up / thumbs-down rating to MongoDB Atlas.
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id", "unknown")
    message_id = data.get("message_id", "msg-1")
    rating = data.get("rating", 1)  # 1 for positive, -1 for negative
    comment = data.get("comment", "")

    mongo_service = getattr(current_app, "mongo_service", None)
    logged = False
    if mongo_service:
        logged = mongo_service.log_feedback(
            session_id=session_id,
            message_id=message_id,
            rating=rating,
            comment=comment
        )

    return jsonify({
        "status": "success",
        "saved_to_mongo": logged,
        "message": "Thank you for your feedback!"
    })

# Quick Picks API Endpoints
@api_bp.route("/quick-picks/coin-flip", methods=["GET", "POST"])
def coin_flip():
    """Simulates a random coin flip."""
    outcome = "Heads" if random.random() < 0.5 else "Tails"
    return jsonify({
        "tool": "Coin Flip",
        "result": outcome,
        "icon": "🪙",
        "explanation": f"The coin landed on {outcome}."
    })

@api_bp.route("/quick-picks/dice-roll", methods=["GET", "POST"])
def dice_roll():
    """Simulates a 6-sided dice roll."""
    sides = int(request.args.get("sides", 6))
    if sides < 2 or sides > 100:
        sides = 6
    value = random.randint(1, sides)
    return jsonify({
        "tool": "Dice Roll",
        "sides": sides,
        "result": value,
        "icon": "🎲",
        "explanation": f"Rolled a {value} on a {sides}-sided die."
    })

@api_bp.route("/quick-picks/random-choice", methods=["POST"])
def random_choice():
    """Picks a random item from user-submitted list."""
    data = request.get_json(silent=True) or {}
    items = data.get("items", [])
    if not isinstance(items, list) or len(items) < 2:
        return jsonify({
            "error_code": "DM-901",
            "error": "Please provide at least 2 items to pick from."
        }), 400

    clean_items = [str(item).strip() for item in items if str(item).strip()]
    if len(clean_items) < 2:
        return jsonify({
            "error_code": "DM-901",
            "error": "Please provide at least 2 non-empty items."
        }), 400

    choice = random.choice(clean_items)
    return jsonify({
        "tool": "Random Pick",
        "result": choice,
        "candidates": clean_items,
        "icon": "🎯",
        "explanation": f"Selected '{choice}' out of {len(clean_items)} candidates."
    })

@api_bp.route("/weather", methods=["GET"])
def weather_check():
    """Weather-based decision API endpoint."""
    decision = get_weather_decision()
    return jsonify(decision)

@api_bp.route("/faqs", methods=["GET"])
def get_faqs_api():
    """
    API endpoint returning all FAQs from SQL database.
    Allows frontend and third-party consumers to load FAQs via API.
    """
    category = request.args.get("category", "").strip()
    search = request.args.get("search", "").strip()

    query = FAQ.query
    if category:
        query = query.filter_by(category=category)
    if search:
        search_filter = f"%{search}%"
        query = query.filter((FAQ.question.ilike(search_filter)) | (FAQ.answer.ilike(search_filter)))

    faqs = query.all()
    return jsonify({
        "status": "success",
        "count": len(faqs),
        "faqs": [f.to_dict() for f in faqs]
    })

@api_bp.route("/error-codes", methods=["GET"])
def get_error_codes_api():
    """API endpoint returning all error codes from SQL database."""
    codes = ErrorCode.query.order_by(ErrorCode.code).all()
    return jsonify({
        "status": "success",
        "count": len(codes),
        "error_codes": [c.to_dict() for c in codes]
    })

@api_bp.route("/support/tickets", methods=["GET"])
def list_tickets_api():
    """CRUD (Read all): Returns all support tickets from SQL database."""
    tickets = SupportTicket.query.order_by(SupportTicket.created_at.desc()).all()
    return jsonify({
        "status": "success",
        "count": len(tickets),
        "tickets": [t.to_dict() for t in tickets]
    })

@api_bp.route("/support/ticket", methods=["POST"])
def create_ticket_api():
    """CRUD (Create): API endpoint to create a support ticket."""
    data = request.get_json(silent=True) or {}
    message = data.get("user_message", "").strip()
    email = data.get("email", "").strip() or None

    if not message:
        return jsonify({"error": "Support ticket message cannot be empty."}), 400

    ticket = SupportTicket(user_message=message, email=email)
    db.session.add(ticket)
    db.session.commit()

    return jsonify({
        "status": "success",
        "ticket": ticket.to_dict()
    }), 201

@api_bp.route("/support/ticket/<ticket_id>", methods=["GET", "PUT", "DELETE"])
def ticket_crud_api(ticket_id):
    """
    Full CRUD operations for Support Tickets:
    - GET: Read ticket by ID
    - PUT: Update ticket status or details
    - DELETE: Remove ticket
    """
    ticket = SupportTicket.query.filter_by(id=ticket_id).first()
    if not ticket:
        return jsonify({"error": f"Ticket '{ticket_id}' not found."}), 404

    if request.method == "GET":
        return jsonify(ticket.to_dict())

    elif request.method == "PUT":
        data = request.get_json(silent=True) or {}
        new_status = data.get("status")
        new_email = data.get("email")
        new_message = data.get("user_message")

        if new_status:
            ticket.status = str(new_status).strip()
        if new_email is not None:
            ticket.email = str(new_email).strip() or None
        if new_message:
            ticket.user_message = str(new_message).strip()

        db.session.commit()
        return jsonify({
            "status": "success",
            "message": f"Ticket '{ticket_id}' updated successfully.",
            "ticket": ticket.to_dict()
        })

    elif request.method == "DELETE":
        db.session.delete(ticket)
        db.session.commit()
        return jsonify({
            "status": "success",
            "message": f"Ticket '{ticket_id}' deleted successfully."
        })

# Dedicated endpoint to easily test 429 rate limit
@api_bp.route("/trigger-rate-limit", methods=["GET"])
def test_rate_limit():
    """Test endpoint with a very low rate limit of 1 per minute."""
    limiter = getattr(current_app, "limiter", None)
    return jsonify({
        "status": "ok",
        "message": "If you call this endpoint repeatedly, Flask-Limiter will trigger HTTP 429 Too Many Requests."
    })
