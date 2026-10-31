import re
import logging
import requests
from app.models import db, FAQ, ErrorCode, SupportTicket

logger = logging.getLogger(__name__)

ERROR_CODE_REGEX = re.compile(r'\b(DM-901|400|401|403|404|429|500|503)\b', re.IGNORECASE)

def detect_error_code(text):
    """Detect known error code patterns in text."""
    match = ERROR_CODE_REGEX.search(text)
    if match:
        return match.group(1).upper()
    return None

def search_faqs(query_text, min_score=1):
    """
    Search FAQ database using token overlap and keyword relevance matching.
    Returns list of tuples (faq, score) sorted by score descending.
    """
    words = re.findall(r'\w+', query_text.lower())
    # Exclude common stopwords
    stopwords = {"a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "is", "it", "are", "do", "how", "what", "can", "i", "my", "me", "this", "that", "there"}
    clean_words = [w for w in words if w not in stopwords and len(w) > 2]
    
    if not clean_words:
        return []

    faqs = FAQ.query.all()
    results = []

    for faq in faqs:
        q_text = faq.question.lower()
        a_text = faq.answer.lower()
        cat_text = faq.category.lower()
        
        score = 0
        for word in clean_words:
            # Question matches carry higher weight
            if word in q_text:
                score += 3
            if word in cat_text:
                score += 2
            if word in a_text:
                score += 1
                
        # Bonus for multi-word exact phrase matches
        if len(clean_words) >= 2:
            phrase = " ".join(clean_words)
            if phrase in q_text:
                score += 5
            elif phrase in a_text:
                score += 3

        if score >= min_score:
            results.append((faq, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results

def call_gemini_api(api_key, prompt, timeout=4.0):
    """Call Google Gemini API with fallback."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [{"text": prompt}]
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 300
        }
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if response.status_code == 200:
        data = response.json()
        candidates = data.get("candidates", [])
        if candidates:
            return candidates[0]["content"]["parts"][0]["text"].strip()
    return None

def call_anthropic_api(api_key, prompt, timeout=4.0):
    """Call Anthropic Claude API with fallback."""
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 300,
        "messages": [{"role": "user", "content": prompt}]
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if response.status_code == 200:
        data = response.json()
        content = data.get("content", [])
        if content:
            return content[0].get("text", "").strip()
    return None

def process_chat_message(user_message, config):
    """
    Implements the complete chat pipeline:
    1. Error code detection & explanation
    2. FAQ search
    3. LLM answer generation using only verified FAQ facts
    4. Auto support ticket creation if cannot answer confidently
    """
    clean_message = (user_message or "").strip()
    if not clean_message:
        return {
            "reply": "Hello! How can I help you make a decision today? You can ask about our Weighted Matrix, Quick Picks, error codes, or troubleshooting.",
            "source": "DefaultGreeting",
            "ticket_id": None
        }

    # Step 1: Check for Error Code query
    error_code = detect_error_code(clean_message)
    if error_code:
        err_obj = ErrorCode.query.filter_by(code=error_code).first()
        if err_obj:
            reply = (
                f"**Error Code {err_obj.code}: {err_obj.title}**\n\n"
                f"{err_obj.description}\n\n"
                f"**Recommended Fix:** {err_obj.suggested_fix}"
            )
            return {
                "reply": reply,
                "source": f"ErrorCode:{err_obj.code}",
                "ticket_id": None
            }

    # Step 2: Search FAQ database
    faq_matches = search_faqs(clean_message, min_score=2)
    if faq_matches:
        best_faq, best_score = faq_matches[0]
        top_faqs = [faq for faq, score in faq_matches[:3]]
        
        # Build context for LLM
        faq_context = "\n\n".join([f"Q: {f.question}\nA: {f.answer}" for f in top_faqs])
        prompt = (
            f"You are the Decision Maker Assistant. Answer the user's question politely and concisely using ONLY "
            f"the factual knowledge below. Do not invent any facts, features, or external information.\n\n"
            f"Verified Facts:\n{faq_context}\n\n"
            f"User Question: {clean_message}\n\n"
            f"Answer:"
        )

        llm_reply = None
        gemini_key = getattr(config, "GEMINI_API_KEY", "")
        anthropic_key = getattr(config, "ANTHROPIC_API_KEY", "")

        # Try Gemini if key available
        if gemini_key:
            try:
                llm_reply = call_gemini_api(gemini_key, prompt)
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}")

        # Try Anthropic if Gemini unavailable and Anthropic key present
        if not llm_reply and anthropic_key:
            try:
                llm_reply = call_anthropic_api(anthropic_key, prompt)
            except Exception as e:
                logger.warning(f"Anthropic API call failed: {e}")

        # Graceful fallback: return synthesized answer directly from matched FAQ
        if not llm_reply:
            llm_reply = f"{best_faq.answer}"

        return {
            "reply": llm_reply,
            "source": f"FAQ:{best_faq.id}",
            "ticket_id": None
        }

    # Step 3: Assistant cannot answer confidently -> Auto-create Support Ticket
    try:
        new_ticket = SupportTicket(
            user_message=clean_message,
            email=None,
            status="Open (Auto-created via AI Chat)"
        )
        db.session.add(new_ticket)
        db.session.commit()
        ticket_id = new_ticket.id
        logger.info(f"Auto-created support ticket {ticket_id} for unanswered query.")
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to auto-create support ticket: {e}")
        ticket_id = "TICK-PENDING"

    fallback_reply = (
        f"I cannot confidently answer your question based on our current verified documentation, "
        f"and I don't want to provide inaccurate advice.\n\n"
        f"I have automatically created a support ticket for our engineering team to review:\n"
        f"🎫 **Ticket ID: {ticket_id}**\n\n"
        f"You can track its status anytime on the **Support** page."
    )

    return {
        "reply": fallback_reply,
        "source": f"AutoTicket:{ticket_id}",
        "ticket_id": ticket_id
    }
