# Decision Maker

> A production-grade, rational choice web application designed to help individuals and teams evaluate alternatives, analyze multi-criteria trade-offs, and make informed choices through mathematical weighting, quick randomizers, and AI-grounded guidance.

* **GitHub Repository:** [https://github.com/prinethakannan262006-alt/decision-maker](https://github.com/prinethakannan262006-alt/decision-maker)
* **Live Render Deployment:** [https://decision-maker-prinethakannan.onrender.com](https://decision-maker-prinethakannan.onrender.com)

---

## 1. Overview & Core Features

Decision Maker combines mathematical rigor, randomized picks, and AI intelligence in a unified responsive web suite:

* **Weighted Decision Matrix:**
  * Define unlimited candidate options and evaluation criteria.
  * Assign importance weights (scale 1 to 5) to each criterion.
  * Score each alternative on a granular 1 to 10 scale.
  * Instant mathematical ranking with weighted score contributions: $\text{Total Score} = \sum (\text{Score}_i \times \text{Weight}_i)$.
  * Permanent persistence to a relational SQL database with one-click saving.
* **Quick Picks Randomization:**
  * **Coin Flip:** Instant 50/50 binary choice with 3D flip animation.
  * **Dice Roll:** Multi-sided die (6, 12, 20, 100 sides) with physics shake animation.
  * **Random List Picker:** Custom comma-separated item randomizer.
* **Outdoor Weather Decision Engine:**
  * Live integration with Open-Meteo REST API.
  * Real-time recommendation ("Should I go outside?") based on temperature, precipitation, and conditions.
  * Built with strict 3-second SLA timeout and automatic resilience fallback.
* **Grounded AI Decision Advisor:**
  * Interactive floating chat panel present across every page (including custom 404/500 pages).
  * Automatically detects and explains system error codes (e.g., 400, 401, 403, 404, 429, 500, 503, DM-901).
  * Answers questions strictly based on verified database FAQs to prevent hallucinations.
  * Automatically creates a support ticket in the SQL database if a question exceeds verified knowledge.
  * Captures thumbs-up and thumbs-down conversational feedback in MongoDB Atlas.
* **Production Observability & Diagnostics:**
  * Structured request logging middleware recording HTTP method, path, response status, duration, and client IP into rotating log files (`logs/app.log`) and console.
  * Live `/health` monitor with dependency checks for SQL database, MongoDB Atlas, and external APIs, returning HTTP 503 if core services fail.
  * Knowledge Base FAQ accordion with category filters and instant keyword search.
  * Diagnostics table detailing all 8 application error codes with interactive test triggers.
  * Support desk with manual ticket submission and tracking by Ticket ID.

---

## 2. Technology Stack

* **Backend:** Python 3.12, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-Limiter 3.8, Gunicorn 23.0
* **Frontend:** Responsive Mobile-First HTML5, Tailwind CSS (via CDN), Custom CSS animations, Vanilla JavaScript (ES6+)
* **SQL Database:** SQLite for local development; PostgreSQL in Render production (ORM powered by SQLAlchemy)
* **NoSQL Database:** MongoDB Atlas via PyMongo for non-blocking conversational logs (`chat_logs`) and feedback ratings (`feedback`)
* **AI Architecture:** LLM service integration (Google Gemini / Anthropic Claude REST API) with intelligent local FAQ fallback engine
* **Observability:** Rotating file logger (5MB cap, 5 backups), request timing middleware, live `/health` endpoint

---

## 3. Environment Variables

All configuration is safely loaded through environment variables. **Never commit actual secret values into git.**

| Variable Name | Description | Example / Default |
| :--- | :--- | :--- |
| `FLASK_ENV` | Environment mode (`development` or `production`) | `production` |
| `SECRET_KEY` | Cryptographic secret for session security | Random 32+ character string |
| `DATABASE_URL` | Relational SQL database URI (SQLite locally, PostgreSQL on Render) | `sqlite:///instance/decision_maker.db` |
| `MONGO_URI` | MongoDB Atlas connection string for chat logs & feedback | `mongodb+srv://...` (Optional, fails gracefully) |
| `GEMINI_API_KEY` | Google Gemini API key for assistant reasoning | Optional (Built-in FAQ fallback used if absent) |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key for assistant reasoning | Optional |
| `ADMIN_TOKEN` | Bearer token for protected `/admin/tickets` access | Secret admin token string |

---

## 4. Local Development Setup

### Prerequisites
* Python 3.11+ (Python 3.12 recommended)
* Git

### Step-by-Step Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/prinethakannan262006-alt/decision-maker.git
   cd decision-maker
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env to adjust any optional keys if desired
   ```

5. **Run test suite:**
   ```bash
   python -m unittest discover -s tests -p "test_*.py"
   ```

6. **Start local development server:**
   ```bash
   python app.py
   ```
   Open your browser at `http://localhost:5000`.

---

## 5. Render Deployment Guide

### Option A: Automatic Blueprint Deployment (Recommended)
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** -> **Blueprint**.
3. Connect your GitHub repository: `prinethakannan262006-alt/decision-maker`.
4. Render will parse `render.yaml` and provision both:
   * **Web Service:** `decision-maker` (runtime Python 3.12, command `gunicorn "app:create_app()"`)
   * **PostgreSQL Database:** `decision-maker-db`
5. Under Environment Variables for the Web Service, add:
   * `MONGO_URI`: Your MongoDB Atlas connection URI (optional).
   * `GEMINI_API_KEY`: Your Gemini API key (optional).
   * `ADMIN_TOKEN`: A secret token for the admin ticket console.
6. Click **Apply**. Database tables and initial FAQs/Error Codes will be automatically created and safely seeded on initial start.

### Option B: Manual Web Service Setup
1. In Render, select **New +** -> **Web Service**.
2. Connect `prinethakannan262006-alt/decision-maker`.
3. Set **Runtime** to `Python 3`.
4. Set **Build Command** to `pip install -r requirements.txt`.
5. Set **Start Command** to `gunicorn "app:create_app()"`.
6. Add environment variables:
   * `FLASK_ENV=production`
   * `PYTHON_VERSION=3.12.10`
   * `SECRET_KEY` (use "Generate")
   * `DATABASE_URL` (link to your Render PostgreSQL instance)
7. Deploy the service.

---

## 6. Proposed Future Improvement

* **Export Decision Reports to PDF/CSV:** Enable users to export their weighted decision breakdown, criteria contributions, and ranking summary as downloadable branded PDF or CSV reports for stakeholder meetings and offline archival.
