# Decision Maker

> A production-grade, rational choice web application designed to help individuals and teams evaluate alternatives, analyze multi-criteria trade-offs, and make informed choices through mathematical weighting, quick randomizers, and AI-grounded guidance. Built with **Django 6.x**, **PostgreSQL**, **MongoDB Atlas**, and **Tailwind CSS**.

* **Live Deployment (HTTPS):** [https://decision-maker-prinethakannan.onrender.com](https://decision-maker-prinethakannan.onrender.com)
* **GitHub Repository:** [https://github.com/prinethakannan262006-alt/decision-maker](https://github.com/prinethakannan262006-alt/decision-maker)

---

## 1. Requirements & Project Checklist Compliance

| Requirement / Checklist Item | Implementation Details & Status |
| :--- | :--- |
| **1. Live HTTPS site, 3+ pages, mobile-friendly** | Deployed on Render with HTTPS. 5 full responsive pages: Home (`/`), Decision Tool (`/decision-tool`), Knowledge Base (`/faqs`), Error Catalog (`/error-codes`), Support Desk (`/support`), plus Admin Portal (`/admin/tickets`). Tested on mobile viewports. |
| **2. Chat widget on every page** | Floating AI assistant widget embedded in base template (`templates/base.html`), rendered across all user pages and error views. |
| **3. 10+ FAQs in SQL, FAQ page from API** | 12 comprehensive FAQs seeded in the relational SQL database (`core_faq`). Dedicated FAQ page (`/faqs`) and REST API (`/api/faqs`) with live category filter and search. |
| **4. 8+ error codes in SQL** | 8 standard and custom error codes (400, 401, 403, 404, 429, 500, 503, and application-specific `DM-901`) seeded in SQL (`core_errorcode`) with explanations, solutions, and live trigger buttons at `/error-codes`. |
| **5. Custom 404 & 500 pages with Ask-Assistant button** | Dedicated custom error handlers (`custom_page_not_found_404`, `custom_server_error_500`) with quick-action "Ask the Assistant" buttons that open the chat pre-filled with error diagnostics. |
| **6. Assistant answers FAQ and explains error codes** | Grounded AI pipeline recognizes error codes in user text and searches database FAQs for exact matches, providing grounded answers and guidance without hallucination. |
| **7. Ticket created when unsure (Full CRUD)** | When the AI assistant cannot answer with confidence, it automatically generates a persistent support ticket with tracking ID (`TICK-XXXXXXXX`). Full CRUD REST API supported at `/api/support/ticket/<id>`. |
| **8. Chats and feedback stored in MongoDB** | MongoDB Atlas stores asynchronous chat logs (`chat_logs`) and thumbs-up/down ratings (`feedback`) with non-blocking, graceful offline fallback if disconnected. |
| **9. Keys in env vars, no secrets in GitHub** | All credentials (`SECRET_KEY`, `DATABASE_URL`, `MONGO_URI`, `GEMINI_API_KEY`, `ADMIN_TOKEN`) are managed through environment variables and `.env` (git-ignored). Secret scanning verified clean. |
| **10. Request logs + health check** | Custom `RequestLoggingMiddleware` logs method, path, response status, duration (ms), and IP to `logs/app.log`. Live `/health` monitor checks SQL, MongoDB, and external API connectivity. |
| **11. Extra third-party call with timeout and fallback** | Outdoor Decision Engine calls Open-Meteo REST API (`core/services/weather_service.py`) with a strict 3-second SLA timeout and deterministic fallback for offline resilience. |
| **12. README with live address & improvement** | Live URL, comprehensive architecture overview, local development instructions, and proposed improvement documented below. |

---

## 2. Core Features & User Workflow

1. **Weighted Decision Matrix (`/decision-tool`):**
   * Dynamically add alternatives and evaluation criteria.
   * Adjust weights (scale 1 to 5) and assign scores (scale 1 to 10).
   * Computes mathematical ranking: $\text{Total Score} = \sum (\text{Score}_i \times \text{Weight}_i)$.
   * One-click save to the SQL database with timestamped history.
2. **Quick Picks Randomization:**
   * **Coin Flip:** 3D coin animation for 50/50 binary choices.
   * **Dice Roll:** Multi-sided die (6, 12, 20, 100 sides) with physics shake animation.
   * **Random Choice:** Random selection from comma-separated custom inputs.
3. **Outdoor Weather Decision Engine:**
   * Fetches real-time weather data from Open-Meteo API.
   * Evaluates temperature, precipitation, and conditions to deliver an outdoor decision with fallback.
4. **Grounded AI Decision Advisor:**
   * Embedded floating chat on every page.
   * Diagnoses HTTP and app errors (400, 401, 403, 404, 429, 500, 503, DM-901).
   * Queries verified FAQ knowledge base.
   * Auto-creates support tickets with unique IDs (`TICK-XXXXXXXX`) when queries exceed verified knowledge.
5. **Support Desk & Admin Portal:**
   * `/support`: Submit tickets or search ticket status by ID.
   * `/admin/tickets`: Secure administrative ticket portal protected by `ADMIN_TOKEN` (HTTP 401 if missing, HTTP 403 if invalid).
6. **Live System Health Monitor (`/health`):**
   * Accessible in browser as an HTML dashboard and via curl as JSON (`Accept: application/json`).
   * Probes database readiness, MongoDB status, weather API response time, and uptime.

---

## 3. Technology Stack

* **Backend Framework:** Python 3.12, **Django 6.1**, Gunicorn 23.0, WhiteNoise 6.12
* **Database (SQL):** SQLite (local development) / PostgreSQL (production on Render via `dj-database-url` and `psycopg[binary]`)
* **Database (NoSQL):** MongoDB Atlas via PyMongo (`chat_logs` and `feedback` collections)
* **Frontend:** Responsive HTML5, Tailwind CSS, FontAwesome 6, Vanilla JavaScript (ES6+)
* **Testing:** Django Test Suite (`python manage.py test core`) covering all 20 test suites

---

## 4. Environment Variables

All settings load from environment variables (`.env` locally, Render Dashboard in production):

| Variable Name | Description | Default / Example |
| :--- | :--- | :--- |
| `SECRET_KEY` | Django security key | Generated random string |
| `DATABASE_URL` | PostgreSQL or SQLite connection string | `sqlite:///db.sqlite3` |
| `MONGO_URI` | MongoDB Atlas URI for chat logs & feedback | `mongodb+srv://...` (Optional, fails gracefully) |
| `GEMINI_API_KEY` | Google Gemini API key for assistant reasoning | Optional (Grounded FAQ fallback used if empty) |
| `ADMIN_TOKEN` | Bearer token for protected `/admin/tickets` | Secret token string |
| `DEBUG` | Django debug toggle (`True` / `False`) | `False` |

---

## 5. Local Setup & Testing

### 1. Clone & create virtual environment
```bash
git clone https://github.com/prinethakannan262006-alt/decision-maker.git
cd decision-maker

# Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run database migrations
```bash
python manage.py migrate
```

### 4. Execute test suite
```bash
python manage.py test core
```
*(All 20 unit and integration tests will run and pass).*

### 5. Run the development server
```bash
python manage.py runserver 5000
```
Open `http://localhost:5000` in your browser.

---

## 6. Render Deployment

The repository includes a ready-to-use `render.yaml` blueprint:

* **Build Command:**
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
  ```
* **Start Command:**
  ```bash
  gunicorn decision_maker.wsgi:application
  ```

---

## 7. Proposed Future Improvement

* **Export Decision Reports to PDF/CSV:** Enable users to export their weighted decision breakdown, criteria contributions, and ranking summary as downloadable branded PDF or CSV reports for stakeholder meetings and offline archival.
