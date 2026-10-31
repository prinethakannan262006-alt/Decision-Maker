import logging
from app.models import db, FAQ, ErrorCode

logger = logging.getLogger(__name__)

INITIAL_FAQS = [
    {
        "question": "How does the Weighted Decision Matrix work?",
        "answer": "The Weighted Decision Matrix allows you to evaluate multiple options against specific criteria. Each criterion is assigned an importance weight from 1 to 5. You score each option against each criterion, and the system computes the weighted sum: Sum(Score * Weight). The option with the highest total score is your ranked winner.",
        "category": "Decision Matrix"
    },
    {
        "question": "What scale should I use for criteria weights and option scores?",
        "answer": "Criteria weights are set on a 1–5 scale (1 = Least Important, 5 = Critical). Individual option scores range from 1 to 10 (1 = Poor fit, 10 = Outstanding fit). This provides granular differentiation when comparing close alternatives.",
        "category": "Decision Matrix"
    },
    {
        "question": "Is my decision data saved automatically in the database?",
        "answer": "Yes! When you complete a weighted decision evaluation, you can click 'Save Decision'. It is securely stored in our SQL database (SQLite locally and PostgreSQL in production). You can review all saved past decisions anytime on the Decision Tool page.",
        "category": "Storage & Privacy"
    },
    {
        "question": "What are Quick Picks and when should I use them?",
        "answer": "Quick Picks are designed for low-stakes or binary choices where deep matrix analysis is unnecessary. We offer Coin Flip for 50/50 choices, 3D Dice Roll for numeric randomisation, and Custom Random Pick to draw randomly from your own custom items.",
        "category": "Quick Picks"
    },
    {
        "question": "How does the AI Decision Advisor assist me?",
        "answer": "The AI Assistant helps you structure complicated choices. It uses verified website documentation and FAQs to guide you on tooling, explains error codes in plain language, and can suggest criteria or evaluate trade-offs. If it cannot answer, it automatically opens a support ticket.",
        "category": "AI Assistant"
    },
    {
        "question": "What happens if the AI Assistant cannot answer my question?",
        "answer": "If your question cannot be reliably answered from verified knowledge bases, the assistant will candidly tell you so, automatically generate a support ticket in the database, and present you with your tracking Ticket ID.",
        "category": "Support"
    },
    {
        "question": "What do the website error codes mean?",
        "answer": "Our system includes standard HTTP status codes (400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Rate Limit, 500 Internal Error, 503 Service Unavailable) and custom codes such as DM-901 (invalid decision matrix inputs). Check our dedicated Error Codes page for detailed fixes.",
        "category": "Error Codes"
    },
    {
        "question": "How do I create and track a support ticket?",
        "answer": "Visit the Support page from the top navigation. Enter your issue message and optional email to receive an instant Ticket ID. You can also paste any Ticket ID in the lookup box to track its current resolution status.",
        "category": "Support"
    },
    {
        "question": "What is error code DM-901 and how can I resolve it?",
        "answer": "DM-901 occurs when you submit an invalid decision matrix evaluation. It requires at least 2 distinct options, at least 1 criterion with a weight between 1 and 5, and non-empty score values. To fix it, verify that your options and criteria rows are filled out properly.",
        "category": "Error Codes"
    },
    {
        "question": "Does the Decision Maker work on smartphones and tablets?",
        "answer": "Yes, Decision Maker is built with a mobile-first responsive architecture. The matrix table supports horizontal fluid scrolling, the navigation bar collapses into a hamburger drawer, and the AI chat panel expands to full width on mobile screens.",
        "category": "General"
    },
    {
        "question": "How is my feedback on AI responses used?",
        "answer": "When you click thumbs-up or thumbs-down on any assistant message, your rating is anonymously logged to our MongoDB Atlas analytics collection. This helps engineers review conversational quality without storing personal sensitive data.",
        "category": "AI Assistant"
    },
    {
        "question": "Can I check system uptime and database health?",
        "answer": "Yes! Visit the /health endpoint or navigate to System Health in the footer. It provides live status checks on SQL database connectivity, MongoDB connection, third-party weather API responsiveness, uptime, and system timestamps.",
        "category": "General"
    }
]

INITIAL_ERROR_CODES = [
    {
        "code": "400",
        "title": "Bad Request",
        "description": "The server could not understand the request due to invalid syntax, missing required fields, or malformed JSON payloads.",
        "suggested_fix": "Double-check your input parameters, ensure JSON payloads are properly formatted, and verify all mandatory form fields are provided."
    },
    {
        "code": "401",
        "title": "Unauthorized",
        "description": "Authentication credentials are missing or invalid. Access to this resource requires a valid authorization token.",
        "suggested_fix": "Provide a valid Authorization header (Bearer <ADMIN_TOKEN>) or pass the admin token parameter in your request."
    },
    {
        "code": "403",
        "title": "Forbidden",
        "description": "The server understood the request, but refuses to authorize it because the provided credentials lack permission.",
        "suggested_fix": "Verify that your account or token has administrative privileges. Contact system administrators if you require elevated access."
    },
    {
        "code": "404",
        "title": "Page or Resource Not Found",
        "description": "The requested URL or resource endpoint could not be found on the Decision Maker server.",
        "suggested_fix": "Check the URL for typographical errors, return to the Home page, or ask our floating AI assistant to help you locate the page."
    },
    {
        "code": "429",
        "title": "Too Many Requests",
        "description": "You have sent too many requests in a given amount of time and breached rate limiting quotas.",
        "suggested_fix": "Please pause and wait 60 seconds before sending further messages or API requests. Automated polling should be throttled."
    },
    {
        "code": "500",
        "title": "Internal Server Error",
        "description": "The server encountered an unexpected condition that prevented it from fulfilling the request.",
        "suggested_fix": "Refresh the page after a few moments. If the issue persists, use our Support page or AI chat to report the incident."
    },
    {
        "code": "503",
        "title": "Service Unavailable",
        "description": "The server is currently unable to handle the request due to a temporary overload, maintenance, or core database downtime.",
        "suggested_fix": "Verify /health to identify which service component is offline, and try reloading after the service has recovered."
    },
    {
        "code": "DM-901",
        "title": "Decision Input Invalid",
        "description": "The decision matrix calculation payload was rejected because it did not meet minimum requirements (e.g. fewer than 2 options, missing criteria, or out-of-bounds weights).",
        "suggested_fix": "Ensure you provide at least 2 options and 1 criterion with weights between 1 and 5. Verify all score inputs contain valid numbers."
    }
]

def seed_database_safely():
    """Seed initial FAQs and Error Codes without duplicating records on restarts."""
    try:
        # Seed FAQs
        for faq_data in INITIAL_FAQS:
            existing = FAQ.query.filter_by(question=faq_data["question"]).first()
            if not existing:
                faq = FAQ(
                    question=faq_data["question"],
                    answer=faq_data["answer"],
                    category=faq_data["category"]
                )
                db.session.add(faq)
        
        # Seed Error Codes
        for err_data in INITIAL_ERROR_CODES:
            existing = ErrorCode.query.filter_by(code=err_data["code"]).first()
            if not existing:
                code_obj = ErrorCode(
                    code=err_data["code"],
                    title=err_data["title"],
                    description=err_data["description"],
                    suggested_fix=err_data["suggested_fix"]
                )
                db.session.add(code_obj)
        
        db.session.commit()
        logger.info("Database successfully seeded/verified without duplicates.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error during database seeding: {e}")
