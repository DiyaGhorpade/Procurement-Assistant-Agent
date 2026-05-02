# ProcureAI — AI-Powered Procurement Negotiation Assistant

A production-ready GenAI system for intelligent vendor evaluation and negotiation strategy generation using LLM + RAG.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                  React.js Frontend                   │
│  Dashboard │ Vendor Recommender │ Price Analysis │   │
│                  Negotiation AI                      │
└────────────────────┬────────────────────────────────┘
                     │ REST API
┌────────────────────▼────────────────────────────────┐
│                FastAPI Backend                       │
│                                                      │
│  /api/v1/ai/recommend-vendors   → Scoring Engine    │
│  /api/v1/ai/price-analysis      → Trend Analysis    │
│  /api/v1/ai/negotiation-strategy → RAG Pipeline     │
└──────────┬──────────────┬───────────────────────────┘
           │              │
    ┌──────▼──────┐  ┌────▼──────────────────────────┐
    │ PostgreSQL  │  │  FAISS + Sentence-Transformers │
    │ (Orders,    │  │  + OpenAI LLM                  │
    │  Vendors,   │  │  (RAG Pipeline)                │
    │  Products)  │  └───────────────────────────────┘
    └─────────────┘
```

## Features

### 1. Vendor Recommendation Engine
- Scores vendors 0–100 across Price (40%), Delivery (30%), Reliability (30%)
- Fully explainable — no black-box AI decisions
- Historical data-driven with percentile rankings

### 2. Historical Price Intelligence
- Detects overpriced / fairly priced / underpriced vendors
- Quantifies negotiation leverage (e.g. "12% above market average")
- Monthly trend charts per vendor × product

### 3. RAG-Based Negotiation Strategy Generator
- FAISS vector index of historical negotiation cases
- Semantic retrieval using Sentence-Transformers (local embeddings)
- LLM generates strategy grounded in retrieved cases (anti-hallucination)
- Falls back to rule-based strategy if no LLM key configured

### 4. REST API
- Full OpenAPI docs at `/docs`
- Clean versioned endpoints under `/api/v1`

---

## Quick Start (Docker)

```bash
# 1. Clone the repo
git clone <repo-url>
cd procurement-assistant

# 2. Set your OpenAI key (optional — rule-based fallback works without it)
export OPENAI_API_KEY=sk-...

# 3. Start everything
docker-compose up --build

# App is available at:
#   Frontend:  http://localhost:3000
#   Backend:   http://localhost:8000
#   API Docs:  http://localhost:8000/docs
```

---

## Local Development (without Docker)

### Backend

```bash
cd backend

# Create venv
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install deps
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your DATABASE_URL and OPENAI_API_KEY

# Run migrations (creates tables)
python -c "from app.core.database import engine, Base; from app.models.models import *; Base.metadata.create_all(bind=engine)"

# Seed data
python seed_db.py

# Start server
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
REACT_APP_API_URL=http://localhost:8000/api/v1 npm start
```

---

## API Reference

### Vendor Recommendation
```http
POST /api/v1/ai/recommend-vendors
{
  "product_id": 1,
  "quantity": 500,
  "top_n": 3
}
```

### Price Analysis
```http
GET /api/v1/ai/price-analysis/{vendor_id}/{product_id}
```

### Negotiation Strategy (RAG)
```http
POST /api/v1/ai/negotiation-strategy
{
  "vendor_id": 1,
  "product_id": 1,
  "quantity": 500,
  "current_quoted_price": 0.52,
  "target_price_reduction_pct": 12.0
}
```

---

## Deployment

### Backend → Render
1. Connect GitHub repo to [render.com](https://render.com)
2. Set root directory to `backend/`
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add env vars: `DATABASE_URL`, `OPENAI_API_KEY`, `CORS_ORIGINS`

### Database → Supabase / Railway
- Create a PostgreSQL instance
- Copy the connection string to `DATABASE_URL`

### Frontend → Vercel
1. Connect GitHub repo
2. Set root directory to `frontend/`
3. Add env var: `REACT_APP_API_URL=https://your-backend.onrender.com/api/v1`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy |
| Database | PostgreSQL |
| Vector DB | FAISS (in-memory) |
| Embeddings | Sentence-Transformers (all-MiniLM-L6-v2) |
| LLM | OpenAI GPT-4o-mini (configurable) |
| Frontend | React.js |
| Deployment | Render + Supabase + Vercel |

---

## Project Structure

```
procurement-assistant/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routers
│   │   ├── core/         # Config, DB session
│   │   ├── models/       # SQLAlchemy models + Pydantic schemas
│   │   ├── rag/          # FAISS + embedding + LLM pipeline
│   │   └── services/     # Business logic (scoring, price analysis)
│   ├── main.py           # App entrypoint
│   ├── seed_db.py        # Data seeder
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/        # Dashboard, VendorRecommender, PriceAnalysis, NegotiationStrategy
│       ├── services/     # API client
│       └── App.js
└── docker-compose.yml
```

---

## Interview Talking Points

- **Why RAG?** Grounds LLM output in real historical cases — prevents hallucination
- **Why FAISS?** Zero-infra vector search; swap to Pinecone for production scale
- **Why explainable scoring?** Procurement decisions need audit trails — LLM ≠ decision-maker
- **Why Sentence-Transformers locally?** No external API call for embeddings; faster, cheaper, private
- **Why FastAPI?** Async-first, auto OpenAPI docs, pydantic validation built-in
