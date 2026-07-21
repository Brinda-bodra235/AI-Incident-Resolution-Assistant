# AI Incident Resolution Assistant

An AI-powered incident resolution assistant designed to act as a **"super-smart Senior IT Engineer"**. It helps IT and Ops teams instantly diagnose server crashes, database errors, and application bugs by analyzing raw logs, retrieving past context, and generating step-by-step solutions using Generative AI.

## ✨ Features

- **Automated Diagnosis:** Paste a raw error log, and the AI determines the root cause instantly.
- **Semantic Memory:** Uses a Vector Database to remember how your team resolved similar issues in the past.
- **Actionable Solutions:** Generates step-by-step troubleshooting guides based on historical context.
- **Smart Escalation:** Automatically assigns tickets to human engineers if the AI's confidence is low or if it's a completely novel issue.
- **Hybrid Data Layer:** Uses PostgreSQL for structured incident tracking and Qdrant for semantic similarity searches.

## 🛠 Tech Stack

- **API Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL (SQLAlchemy + Alembic)
- **Vector Database**: Qdrant
- **Generative AI**: Google Gemini API (or OpenAI API)
- **Deployment**: Docker & Docker Compose
- **CI/CD**: GitHub Actions

## 🧠 How it Works (The Pipeline)

When an error log is submitted, the system executes a 6-step pipeline:

1. **Log Parser:** Cleans and extracts the core error message.
2. **Embedding Service:** Uses Gemini to convert the text into mathematical vectors.
3. **Qdrant DB:** Performs a similarity search to find past resolved incidents that match.
4. **LLM Agent (Root Cause):** Analyzes the current error alongside past context to deduce the root cause.
5. **LLM Agent (Solution):** Generates actionable, step-by-step resolution instructions.
6. **PostgreSQL:** Saves the analysis, resolutions, and escalations.

## 🚀 Setup & Running Locally

1. **Clone & Configure**
   ```bash
   git clone <repo-url>
   cd incident-resolution-assistant
   cp .env.example .env
   ```
   *Edit `.env` and add your `GEMINI_API_KEY` (or `OPENAI_API_KEY`).*

2. **Run with Docker Compose**
   ```bash
   docker-compose up --build -d
   ```
   This spins up:
   - **FastAPI app** on `http://localhost:8000` (Visit `http://localhost:8000/docs` for the UI)
   - **PostgreSQL database** on port `5432`
   - **Qdrant vector database** on port `6333`

3. **Run Database Migrations**
   Initializes the database tables inside the running container:
   ```bash
   docker-compose exec api alembic upgrade head
   ```

4. **Testing**
   Run the pytest suite to ensure the AI pipeline and API endpoints are functioning correctly:
   ```bash
   docker-compose exec api env PYTHONPATH=. pytest -v
   ```

## 📚 API Usage Example

Once running, head to the interactive Swagger UI at **http://localhost:8000/docs** to log in and authorize. 

You can then submit an incident like this:

```bash
curl -X POST "http://localhost:8000/incidents/" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "raw_log": "ERROR: ConnectionTimeoutException at db:5432. Unable to reach database."
  }'
```
