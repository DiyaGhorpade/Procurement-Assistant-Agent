---

## Executive Summary

**ProcureAI** is a production-ready GenAI system designed to automate and optimize procurement negotiations. It combines three core capabilities:

1. **Explainable Vendor Recommendation Engine** — Scores vendors using transparent business rules (40% price, 30% delivery, 30% reliability)
2. **Historical Price Intelligence** — Detects overpriced vendors and quantifies negotiation leverage with market data
3. **RAG-Based Negotiation Strategy Generator** — Retrieves similar historical negotiation cases and generates LLM-grounded strategies grounded in real data

The application processes 500 real procurement transactions across 7 suppliers, 10 products, and 6 product categories, enabling data-driven procurement decisions without AI black-boxes.

---

## What This Is

**ProcureAI** solves the problem of **manual, bias-prone procurement negotiations**. Procurement teams typically rely on spreadsheets, gut instinct, or ad-hoc market research. This system provides:

- **Objective vendor scoring** based on 500 historical transactions
- **Quantified negotiation leverage** ("Vendor is 22% above market — request 15% reduction")
- **Case-grounded strategies** from 10+ historical negotiation precedents
- **Explainable AI** — every recommendation shows its reasoning

**Who uses it:** Procurement teams, supply chain managers, and procurement officers at mid-market companies.

---

## Tech Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.x, FastAPI 0.111.0, SQLAlchemy 2.0.30 |
| **Database** | PostgreSQL 15 (relational, via psycopg2) |
| **Vector Search** | FAISS (in-memory, CPU-only) |
| **Embeddings** | Sentence-Transformers `all-MiniLM-L6-v2` (local, no external API) |
| **LLM** | OpenAI GPT-4o-mini (with rule-based fallback) |
| **Frontend** | React.js 18.3.1, Recharts 2.12.5, Axios 1.7.2 |
| **Containerization** | Docker + Docker Compose |
| **Deployment** | Render (backend) + Supabase/Railway (DB) + Vercel (frontend) |

---

## Repository Structure

```
procurement-assistant/
├── data/
│   └── spend_analysis_dataset.csv          # 500 procurement transactions
├── backend/
│   ├── main.py                             # FastAPI app entry point
│   ├── seed_db.py                          # CSV → PostgreSQL ingestion
│   ├── requirements.txt                    # Python dependencies
│   ├── Dockerfile                          # Container image
│   └── app/
│       ├── api/
│       │   ├── data.py                     # CRUD routers (vendors, products, orders)
│       │   └── intelligence.py             # AI endpoints (recommend, analyze, negotiate)
│       ├── core/
│       │   ├── config.py                   # Environment variables & settings
│       │   └── database.py                 # SQLAlchemy engine & session
│       ├── models/
│       │   ├── models.py                   # SQLAlchemy ORM: Vendor, Product, PurchaseOrder, PriceRecord
│       │   └── schemas.py                  # Pydantic request/response schemas
│       ├── services/
│       │   ├── vendor_scoring.py           # Vendor recommendation engine
│       │   ├── price_analysis.py           # Historical price intelligence
│       │   └── negotiation.py              # Orchestrates RAG + price analysis
│       └── rag/
│           └── pipeline.py                 # FAISS indexing + LLM generation
├── frontend/
│   ├── package.json                        # NPM dependencies
│   ├── Dockerfile                          # React container
│   └── src/
│       ├── App.js                          # Main router & sidebar nav
│       ├── index.js                        # React entry point
│       ├── index.css                       # Design system & component styles
│       ├── pages/
│       │   ├── Dashboard.js                # Overview, stats, quick actions
│       │   ├── VendorRecommender.js        # Vendor scoring UI
│       │   ├── PriceAnalysis.js            # Price trend charts & leverage
│       │   └── NegotiationStrategy.js      # RAG strategy generator UI
│       └── services/
│           └── api.js                      # Axios HTTP client wrapper
└── docker-compose.yml                      # Multi-container orchestration
```

---

## How It Fits Together: Data & Request Flow

### Data Pipeline
1. **CSV → Database** (`seed_db.py`):
   - Reads `spend_analysis_dataset.csv` (500 rows)
   - Maps CSV columns: `Supplier` → `vendors` table, `ItemName` → `products`, rows → `purchase_orders`
   - Simulates realistic delivery times & quality ratings per supplier profile
   
2. **Database Schema** (PostgreSQL):
   - `vendors`: name, category, country, contact_email
   - `products`: sku, name, category, unit
   - `purchase_orders`: vendor_id, product_id, quantity, unit_price, total_amount, order_date, delivery_days, delivery_status, quality_rating
   - `price_records`: vendor_id, product_id, unit_price, recorded_at (for historical tracking)

### Request-to-Response Flow

**User → Frontend → Backend → Services → Database/RAG → LLM**

1. User selects a product and quantity on the React frontend
2. Frontend calls `/api/v1/ai/recommend-vendors` (POST)
3. **Backend** (`intelligence.py` router):
   - Passes request to `vendor_scoring.recommend_vendors()`
4. **Vendor Scoring Service** (`vendor_scoring.py`):
   - Queries purchase_orders table for historical data per vendor
   - Computes 3 normalized scores:
     - **Price Score (40%)**: Percentile rank; lower price = higher score
     - **Delivery Score (30%)**: Inverse of avg delivery days
     - **Reliability Score (30%)**: 60% on-time rate + 40% quality rating
   - Returns top-N vendors sorted by composite score
5. Frontend displays results with score breakdown charts (Recharts)

---

## Core Algorithms & Logic

### 1. Vendor Recommendation Engine (`vendor_scoring.py`)

**Algorithm: Weighted Multi-Criterion Scoring**

```
For each vendor V and product P:
  1. Fetch historical orders: H = PurchaseOrders where product_id=P
  
  2. Compute stats per vendor:
     avg_price[V] = mean(unit_price) for orders by V
     avg_delivery[V] = mean(delivery_days) for orders by V
     on_time_rate[V] = count(status='on_time') / total_orders * 100
     avg_quality[V] = mean(quality_rating) for orders by V
  
  3. Normalize scores to 0–100:
     price_score[V] = (1 - (price[V] - min_price) / (max_price - min_price)) * 100
     delivery_score[V] = (1 - (days[V] - min_days) / (max_days - min_days)) * 100
     quality_score[V] = (quality[V] / 5.0) * 100
     reliability[V] = 0.6 * on_time_rate[V] + 0.4 * quality_score[V]
  
  4. Composite score:
     total_score[V] = 0.40 * price_score + 0.30 * delivery_score + 0.30 * reliability
  
  5. Sort by total_score descending, return top N
```

**Key Design Decision:** Explainability. Every component is a simple formula with no ML black-box. Procurement officers can defend score to executives.

---

### 2. Historical Price Intelligence (`price_analysis.py`)

**Algorithm: Market Deviation Analysis + Trend Extraction**

```
For vendor V, product P:
  1. Market Average:
     market_avg = mean(unit_price) across ALL vendors for P
  
  2. Vendor Average:
     vendor_avg = mean(unit_price) for V's orders of P
  
  3. Price Deviation:
     deviation_pct = ((vendor_avg - market_avg) / market_avg) * 100
  
  4. Price Status Classification:
     if deviation_pct > 10:    status = "overpriced"      (strong leverage)
     elif deviation_pct < -10: status = "underpriced"     (lock-in opportunity)
     else:                     status = "fairly_priced"   (non-price terms)
  
  5. Monthly Trend:
     For each month in order history:
       trend.append({
         period: "YYYY-MM",
         avg_price: mean(unit_price),
         min_price: min(unit_price),
         max_price: max(unit_price),
         order_count: count()
       })
```

**Output:** Actionable recommendations e.g., "Vendor is 22% above market. Cite market average of $X. Request 15% reduction or invite competing bids."

---

### 3. RAG-Based Negotiation Strategy (`rag/pipeline.py`)

**Algorithm: Semantic Retrieval + LLM Generation**

#### 3a. FAISS Index Construction (Startup)

```
1. Load 10 built-in negotiation cases (case_001 to case_010)
   Each case contains: title, context, product_category, price_deviation_pct, 
                       outcome, tactics_used
  
2. Embed corpus:
   For each case C:
     text = C.title + " " + C.context + " " + C.product_category
     embedding[C] = SentenceTransformer.encode(text, normalize=True)
     # Returns 384-dim vector (all-MiniLM-L6-v2)
  
3. Build FAISS index:
   index = faiss.IndexFlatIP(dim=384)
   # IndexFlatIP = inner-product on L2-normalized vectors
   # = cosine similarity
   index.add(embeddings.astype("float32"))
```

#### 3b. Semantic Retrieval (Per Request)

```
Query: "overpriced vendor electronics laptop price +22% deviation negotiation 
         quantity 500"

1. Embed query:
   q_vec = SentenceTransformer.encode(query, normalize=True)
   
2. Search FAISS:
   scores, indices = index.search(q_vec, top_k=3)
   # Returns 3 most similar cases with cosine similarity scores
   
3. Return retrieved cases with:
   - case_id, title, similarity_score (0-1)
   - outcome (e.g., "15% reduction achieved")
   - tactics_used (e.g., ["competitor benchmarking", "walk-away threat"])
```

#### 3c. LLM-Grounded Strategy Generation

```
If OPENAI_API_KEY is set:
  1. Construct context:
     system_prompt = "You are an expert procurement negotiation advisor. 
                      Generate grounded strategies based on real data."
     
     user_prompt = """
       VENDOR: QuickDeliver Ltd.
       PRODUCT: Laptop
       QUANTITY: 500
       QUOTED: $0.52/unit
       MARKET AVG: $0.45/unit
       DEVIATION: +15.6% (overpriced)
       TARGET: $0.44/unit
       
       Similar cases (from FAISS retrieval):
       - [case_001] Laptop overpriced 22%...
         Tactics: competitor benchmarking, walk-away threat
         Outcome: 15% reduction achieved
       
       Generate a negotiation strategy...
     """
  
  2. Call OpenAI (GPT-4o-mini):
     response = client.chat.completions.create(
       model="gpt-4o-mini",
       messages=[system, user],
       temperature=0.3,  # Low variance for consistency
       max_tokens=800
     )
  
  3. Parse response:
     Extract talking points (lines starting with "•")
     Extract confidence level (search for "CONFIDENCE: [Low|Medium|High]")

Else (fallback, no LLM key):
  Generate rule-based strategy:
  if overpriced:
    "Present market benchmark. Request alignment or competitor quotes.
     Based on similar cases, try: competitor benchmarking, walk-away threat.
     Target: $0.44/unit. Set 5-day deadline."
  else:
    "Fairly priced. Focus on non-price terms: volume discounts, 
     payment terms, delivery SLAs."
```

**Why RAG?** Prevents hallucination. Every strategy is grounded in real, retrieved cases. LLM is a narrative generator, not a decision-maker.

---

## API Reference

### Health Endpoints

```http
GET /health
Response: { "status": "healthy", "rag_ready": true }

GET /
Response: { "status": "ok", "service": "AI Procurement Negotiation Assistant" }
```

### Data Endpoints (CRUD)

#### Vendors
```http
GET /api/v1/vendors
Response: [{ "id": 1, "name": "CloudSoft Corp.", "category": "Software", 
             "country": "USA", "contact_email": "procurement@cloudsoft.com", 
             "created_at": "2026-05-02T..." }]

POST /api/v1/vendors
Body: { "name": "NewVendor", "category": "Electronics", "country": "USA" }
Response: { "id": 8, "name": "NewVendor", ... }

GET /api/v1/vendors/{vendor_id}
Response: { "id": 1, "name": "CloudSoft Corp.", ... }
```

#### Products
```http
GET /api/v1/products
Response: [{ "id": 1, "sku": "LAPT001", "name": "Laptop", "category": "Electronics" }]

POST /api/v1/products
Body: { "sku": "DESK001", "name": "Desk Chair", "category": "Furniture", "unit": "piece" }
Response: { "id": 8, "sku": "DESK001", ... }
```

#### Purchase Orders
```http
GET /api/v1/orders?vendor_id=1&product_id=2
Response: [{ "id": 1, "vendor_id": 1, "product_id": 2, "quantity": 500, 
             "unit_price": 52.00, "total_amount": 26000, "order_date": "2026-03-15T...",
             "delivery_days": 4, "delivery_status": "on_time", "quality_rating": 4.5 }]

POST /api/v1/orders
Body: { "vendor_id": 1, "product_id": 2, "quantity": 100, "unit_price": 50.0 }
Response: { "id": 501, "total_amount": 5000, ... }
```

### AI Intelligence Endpoints

#### 1. Vendor Recommendation
```http
POST /api/v1/ai/recommend-vendors
Content-Type: application/json

Request Body:
{
  "product_id": 1,
  "quantity": 500,
  "top_n": 3
}

Response:
{
  "product": { "id": 1, "sku": "LAPT001", "name": "Laptop", ... },
  "quantity": 500,
  "recommendations": [
    {
      "vendor": { "id": 2, "name": "QuickDeliver Ltd.", ... },
      "score_breakdown": {
        "price_score": 85.5,
        "delivery_score": 95.0,
        "reliability_score": 88.2,
        "total_score": 89.1,
        "price_percentile": 75.0,
        "avg_delivery_days": 3,
        "on_time_rate": 95.0,
        "avg_quality": 4.0,
        "total_orders": 42
      },
      "rank": 1,
      "recommendation": "Top pick. Strongest overall performance across price, 
                         delivery and reliability."
    },
    { ... rank 2 ... },
    { ... rank 3 ... }
  ],
  "analysis_note": "Scored 5 vendors with historical data for 'Laptop'. 
                    Weights: Price 40%, Delivery 30%, Reliability 30%."
}
```

#### 2. Price Analysis
```http
GET /api/v1/ai/price-analysis/{vendor_id}/{product_id}
GET /api/v1/ai/price-analysis/2/1

Response:
{
  "vendor_id": 2,
  "vendor_name": "QuickDeliver Ltd.",
  "product_id": 1,
  "product_name": "Laptop",
  "current_market_avg": 45.8500,
  "vendor_avg_price": 52.0000,
  "price_deviation_pct": 13.45,
  "price_status": "overpriced",
  "negotiation_leverage": "Vendor is 13.5% above market average — 
                           strong leverage to negotiate.",
  "trend": [
    {
      "period": "2024-03",
      "avg_price": 50.2500,
      "min_price": 48.0000,
      "max_price": 52.5000,
      "order_count": 8
    },
    { ... more months ... }
  ],
  "recommendation": "Cite market average of $45.85. Request a 10% reduction 
                     to align with peer pricing."
}
```

#### 3. Negotiation Strategy (RAG)
```http
POST /api/v1/ai/negotiation-strategy
Content-Type: application/json

Request Body:
{
  "vendor_id": 2,
  "product_id": 1,
  "quantity": 500,
  "current_quoted_price": 52.00,
  "target_price_reduction_pct": 12.0
}

Response:
{
  "vendor_name": "QuickDeliver Ltd.",
  "product_name": "Laptop",
  "price_analysis": { ... full price analysis response ... },
  "retrieved_cases": [
    {
      "case_id": "case_001",
      "title": "Laptop overpriced 22% — leveraged competitor quote to get reduction",
      "similarity_score": 0.8765,
      "outcome": "15% reduction achieved. Supplier matched partial discount 
                  after escalation.",
      "tactics_used": ["competitor benchmarking", "walk-away threat", "deadline pressure"]
    },
    { ... case 2 ... },
    { ... case 3 ... }
  ],
  "strategy": "QuickDeliver Ltd. is quoting $52.00/unit, which is 13.5% above 
               the market average of $45.85/unit. This gives you strong leverage 
               to negotiate.\n\nStrategy: Present the market benchmark data directly. 
               Request alignment to market average or provide competitor quotes to 
               justify your position. Based on similar historical cases, tactics like 
               competitor benchmarking, walk-away threat, deadline pressure have 
               worked well.\n\nTarget: Push for $45.76/unit. Be prepared to walk 
               away or invite competing bids if the vendor does not move.",
  "key_talking_points": [
    "Cite market average of $45.85 as your opening data point",
    "Request price match or written justification for premium",
    "Offer extended payment terms in exchange for immediate price reduction",
    "Set a 5-business-day deadline for revised quote"
  ],
  "recommended_target_price": 45.76,
  "confidence_level": "High"
}
```

---

## Frontend Architecture

### App Structure (React SPA)

**Navigation:** 4-page single-page application

1. **Dashboard** (`Dashboard.js`)
   - Overview stats (total vendors, products, savings %, overpriced vendors)
   - Monthly procurement spend chart (Recharts bar chart)
   - Top vendors by score ranking
   - Quick action buttons to navigate to other pages

2. **Vendor Recommender** (`VendorRecommender.js`)
   - Form: Product selector, quantity input, top-N dropdown
   - Calls `POST /api/v1/ai/recommend-vendors`
   - Results: Ranked vendor cards with score breakdowns
   - Visual score bars (price, delivery, reliability) per vendor
   - Explainable recommendation text per vendor

3. **Price Analysis** (`PriceAnalysis.js`)
   - Form: Vendor & product selector
   - Calls `GET /api/v1/ai/price-analysis/{vendor_id}/{product_id}`
   - Results: Price deviation display, market vs vendor comparison
   - **Line chart** showing monthly price trends (Recharts)
   - Reference line showing market average
   - Negotiation leverage & recommendation text

4. **Negotiation Strategy** (`NegotiationStrategy.js`)
   - Form: Vendor, product, quantity, quoted price, target reduction %
   - Calls `POST /api/v1/ai/negotiation-strategy`
   - Results: 
     - Price analysis summary
     - Retrieved similar cases (case ID, title, tactics, outcome)
     - LLM-generated strategy narrative
     - Talking points (bulleted list)
     - Recommended target price
     - Confidence level badge

### Design System

- **CSS Variables** (`index.css`):
  - Colors: Primary accent (`#6366f1`), danger red, success green, info blue
  - Typography: Display font (headings), system font (body)
  - Spacing: 8px grid
  - Components: Cards, buttons (primary/ghost), badges, stat cards, charts

- **UI Components:**
  - Score bars with percentage fills
  - Status badges (overpriced, fairly_priced, underpriced)
  - Rank badges (1st, 2nd, 3rd place styling)
  - Loading spinners
  - Error messages

### HTTP Client (`api.js`)

```javascript
const BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8000/api/v1";

// All requests wrapped in axios instance with auto-JSON handling
export const getVendors = () => api.get("/vendors").then(r => r.data);
export const getProducts = () => api.get("/products").then(r => r.data);
export const recommendVendors = (productId, quantity, topN) =>
  api.post("/ai/recommend-vendors", { product_id: productId, quantity, top_n: topN });
export const getPriceAnalysis = (vendorId, productId) =>
  api.get(`/ai/price-analysis/${vendorId}/${productId}`);
export const getNegotiationStrategy = (payload) =>
  api.post("/ai/negotiation-strategy", payload);
```

---

## Data: Dataset & Seeding

### Dataset: `spend_analysis_dataset.csv`

**Format:** 500 procurement transactions, 7 suppliers, 10 products, 6 categories

**Columns:**
- `TransactionID`: Unique transaction identifier
- `ItemName`: Product name (Laptop, Monitor, Printer, Printer Ink, Desk Chair, Whiteboard, Stapler, Notepad, Laptop Bag, Annual Software License)
- `Category`: Product category (Electronics, Furniture, Stationery, Office Supplies, Accessories, Software)
- `Quantity`: Order quantity (integer)
- `UnitPrice`: Price per unit
- `TotalCost`: Quantity × UnitPrice
- `PurchaseDate`: Order date (YYYY-MM-DD format, distributed across 2024)
- `Supplier`: Vendor name (TechMart Inc., CloudSoft Corp., OfficeSupplies Co., QuickDeliver Ltd., FurniWorks Ltd.)
- `Buyer`: Purchasing manager name

### Supplier Profiles (Synthetic Attributes)

| Supplier | Avg Delivery | On-Time Rate | Avg Quality | Country |
|----------|---|---|---|---|
| **QuickDeliver Ltd.** | 3 days | 95% | 4.0 / 5 | Singapore |
| **CloudSoft Corp.** | 4 days | 92% | 4.5 / 5 | USA |
| **TechMart Inc.** | 5 days | 88% | 4.3 / 5 | USA |
| **OfficeSupplies Co.** | 7 days | 80% | 3.8 / 5 | UK |
| **FurniWorks Ltd.** | 10 days | 65% | 3.4 / 5 | China |

### Seeding Process (`seed_db.py`)

```python
1. Read CSV:
   df = pd.read_csv("spend_analysis_dataset.csv")

2. Create vendors:
   For each unique Supplier:
     - Extract top category for that supplier
     - Assign country & email from SUPPLIER_PROFILES
     - Insert into vendors table

3. Create products:
   For each unique ItemName:
     - Generate SKU (slugified first 6 chars + sequence number)
     - Insert into products table

4. Create purchase_orders:
   For each CSV row:
     - Look up vendor_id and product_id
     - Derive delivery_days & delivery_status using Gaussian distribution
       (weighted by supplier profile; realistic variance)
     - Derive quality_rating (1-5 scale, weighted by profile)
     - Insert into purchase_orders table

5. Insert into PostgreSQL:
   db.commit()  # All 500 orders + relations
```

**Derivation Logic:**
- **Delivery days**: `max(1, round(gauss(avg_delivery, avg_delivery * 0.4)))`
  - QuickDeliver: mean=3, stdev=1.2 → mostly 2-4 days
  - FurniWorks: mean=10, stdev=4 → 6-14 days, slower
  
- **On-time status**: `random() < on_time_rate`
  - QuickDeliver: 95% on-time, 5% late
  - FurniWorks: 65% on-time, 35% late
  
- **Quality rating**: `gauss(avg_quality, 0.4) clamped to [1.0, 5.0]`
  - CloudSoft: mean=4.5 → consistently high
  - FurniWorks: mean=3.4 → lower, more variance

---

## Environment & Configuration

### Backend Configuration (`app/core/config.py`)

```python
class Settings(BaseSettings):
    DATABASE_URL: str                # PostgreSQL connection string
    OPENAI_API_KEY: str              # Optional; falls back to rule-based
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    FAISS_INDEX_PATH: str = "./data/faiss_index"
    NEGOTIATION_CASES_PATH: str = "./data/negotiation_cases.json"
    CORS_ORIGINS: str = '["http://localhost:3000"]'  # JSON string
    
    @property
    def cors_origins_list(self) -> List[str]:
        return json.loads(self.CORS_ORIGINS)  # Parse to list
    
    class Config:
        env_file = ".env"  # Load from .env file
```

### Docker Environment (`docker-compose.yml`)

```yaml
services:
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: procurement
      POSTGRES_PASSWORD: procurement
      POSTGRES_DB: procurement_db
    healthcheck: Waits for DB to be ready before starting backend

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql://procurement:procurement@db:5432/procurement_db
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}  # From .env or environment
      LLM_MODEL: gpt-4o-mini
      EMBEDDING_MODEL: all-MiniLM-L6-v2
      CORS_ORIGINS: '["http://localhost:3000"]'
    volumes:
      - ./data:/app/data:ro  # Read-only CSV data
    command: seed_db.py && uvicorn main:app --reload

  frontend:
    build: ./frontend
    environment:
      REACT_APP_API_URL: http://localhost:8000/api/v1
```

### Quick Start (Docker)

```bash
# 1. Clone and navigate
git clone <repo-url>
cd procurement-assistant

# 2. Configure environment
export OPENAI_API_KEY=sk-...

# 3. Start all services
docker-compose up --build

# 4. Access
Frontend:  http://localhost:3000
Backend:   http://localhost:8000
API Docs:  http://localhost:8000/docs  (Swagger UI)
```

---

## Interview Talking Points

### 1. **Why RAG?**
- **Without RAG:** LLM generates strategies from training data → hallucinates tactics that never worked in your company's context
- **With RAG:** LLM sees 10 real negotiation cases (supplier benchmarking, volume tiering, SLA bundling) → generates strategies grounded in precedent
- **Tradeoff:** Slower (retrieval + generation) vs. more trustworthy for procurement (compliance, audit trails matter)

### 2. **Why FAISS?**
- **Advantage:** Zero infrastructure overhead; runs in-memory on CPU; fast semantic search
- **Limitation:** In-memory only (doesn't scale beyond ~100k cases easily); no persistence
- **Production upgrade:** Swap FAISS for Pinecone or Weaviate (managed, serverless, distributed)

### 3. **Why Explainable Scoring, Not ML?**
- Procurement teams **must defend** vendor decisions to CFOs and legal
- A black-box neural net scoring model is **non-compliant** for procurement audits
- Transparent weighted formula (price 40%, delivery 30%, reliability 30%) is auditable and defensible
- **Tradeoff:** Less adaptive (weights are fixed) vs. more trustworthy (every score is reproducible)

### 4. **Why Sentence-Transformers Locally?**
- **Alternative:** Use OpenAI's embeddings API
- **Why local:** 
  - **No API calls** for embeddings (faster, fewer failures)
  - **Privacy** — your negotiation cases stay in-house
  - **Cost** — embeddings are free (trained once at startup)
  - **Dependency reduction** — one less external API to manage
- **Limitation:** all-MiniLM-L6-v2 is smaller (384 dims) than OpenAI's larger models; trade semantic precision for efficiency

### 5. **Why FastAPI?**
- **Async-first:** Handles concurrent requests without threading headaches
- **Auto-docs:** Swagger UI at `/docs` — no manual OpenAPI maintenance
- **Pydantic:** Request/response validation, automatic JSON serialization
- **DX:** Modern Python (async/await, type hints) vs. Flask's synchronous style

### 6. **Database Design**
- **Relational, normalized:** Vendor → many PurchaseOrders ← Product
- **Why not NoSQL?** Procurement data is highly relational; transactions need ACID guarantees (payment reconciliation)
- **Why PostgreSQL?** ACID compliant, supports complex queries for price analysis, cost-effective

### 7. **Vendor Scoring Algorithm**
- **Three independent dimensions:** Price, Delivery, Reliability
- **Normalization:** Min-max scaling (0–100 per dimension) handles different unit ranges ($ vs days)
- **Weighting:** 40-30-30 reflects typical procurement priorities (price first, then speed+reliability)
- **Percentile ranking:** Shows where each vendor sits in the peer group (e.g., "top 75% for price")

### 8. **Price Analysis Logic**
- **Market baseline:** Mean price across all vendors for a product (removes outliers via mean; median would be more robust)
- **Deviation classification:** ±10% threshold distinguishes overpriced (negotiate hard) vs. underpriced (lock-in) vs. fair (non-price terms)
- **Trend extraction:** Monthly aggregates reveal seasonality, bulk-order discounts, supplier improvements over time

### 9. **RAG Case Retrieval**
- **Corpus:** 10 manually curated negotiation precedents (real-world outcomes, tactics, products)
- **Embedding:** SentenceTransformer encodes case title + context + product category
- **Search:** Query (vendor + product + price deviation) is embedded and matched to top-3 similar cases via cosine similarity
- **Why semantic (not keyword)?** "bulk discount negotiation" and "volume commitment" are synonymous; keyword search misses the connection

### 10. **Fallback Strategy (No LLM Key)**
- If `OPENAI_API_KEY` is not set, RAG pipeline generates rule-based strategies automatically
- Rules: If overpriced → "cite market data, request price match, set deadline"; if fairly priced → "focus on volume, terms, SLAs"
- **Implication:** System is usable offline or with limited budget (no OpenAI costs, but lower quality narratives)

### 11. **Deployment Architecture**
- **Backend:** Render.com (auto-scales, integrates with GitHub)
- **Database:** Supabase PostgreSQL (managed, hourly backups)
- **Frontend:** Vercel (static hosting, CI/CD from GitHub)
- **Why microservices?** Each layer can scale independently; frontend serves static assets globally; backend handles compute

### 12. **Future Enhancements**
- **Multi-year price tracking:** Detect long-term vendor trends (improving reliability, inflation)
- **Supplier risk scores:** Credit checks, geopolitical risk, supply chain resilience
- **Automated alerts:** "FurniWorks is 25% overpriced — negotiate now" push notifications
- **Advanced RAG:** Ingest company's own historical contracts, emails, meeting notes as context

---

## Key Files Deep Dive

### `backend/main.py` — App Lifecycle

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create DB tables, load FAISS index + embedding model
    Base.metadata.create_all(bind=engine)
    rag_pipeline.initialise()  # Heavy I/O (loads 1GB model)
    yield
    # Shutdown: Cleanup (if any)

app = FastAPI(title="...", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins_list, ...)
app.include_router(data.router, prefix="/api/v1")      # CRUD routes
app.include_router(intelligence.router, prefix="/api/v1")  # AI routes
```

**Key Pattern:** FastAPI's `lifespan` context manager replaces the old `@app.on_event("startup")` pattern. Ensures FAISS and models are loaded once, not per-request.

### `backend/app/rag/pipeline.py` — RAG Pipeline Internals

**Initialization:**
```python
def initialise(self):
    # 1. Load Sentence-Transformer (all-MiniLM-L6-v2, ~80MB)
    self.model = SentenceTransformer(settings.EMBEDDING_MODEL)
    
    # 2. Load case corpus (10 built-in cases or from JSON file)
    self.cases = load_cases_from_file_or_builtin()
    
    # 3. Embed and build FAISS index
    corpus_texts = [f"{c['title']} {c['context']} {c['product_category']}" 
                     for c in self.cases]
    embeddings = self.model.encode(corpus_texts, normalize_embeddings=True)
    # normalize_embeddings=True → L2 normalized, suitable for cosine similarity
    
    self.index = faiss.IndexFlatIP(dim=384)  # Inner-product (cosine) index
    self.index.add(embeddings.astype("float32"))
    
    # 4. Init LLM client (if API key provided)
    if settings.OPENAI_API_KEY:
        self.llm_client = OpenAI(api_key=...)
```

**Retrieval:**
```python
def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedCase]:
    # 1. Embed query using same model (consistency!)
    q_vec = self.model.encode([query], normalize_embeddings=True)
    
    # 2. Search index
    scores, indices = self.index.search(q_vec, top_k)
    # scores: array of cosine similarities [0.87, 0.82, 0.76]
    # indices: array of case indices [2, 7, 5]
    
    # 3. Map results to case objects + metadata
    for score, idx in zip(scores[0], indices[0]):
        case = self.cases[idx]
        results.append(RetrievedCase(
            case_id=case["id"],
            title=case["title"],
            similarity_score=round(float(score), 4),
            outcome=case["outcome"],
            tactics_used=case["tactics_used"],
        ))
    return results
```

**Strategy Generation (With LLM):**
```python
def generate_strategy(...) -> (strategy_text, talking_points, target_price, confidence):
    # 1. Build LLM context from retrieved cases
    cases_context = "\n".join([
        f"- [{c.case_id}] {c.title}\n"
        f"  Tactics: {', '.join(c.tactics_used)}\n"
        f"  Outcome: {c.outcome}"
        for c in retrieved_cases
    ])
    
    # 2. Call OpenAI with grounding
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a procurement expert..."},
            {"role": "user", "content": f"VENDOR: {vendor_name}...\n\n{cases_context}\n\nGenerate strategy..."}
        ],
        temperature=0.3,  # Low temp for consistency
        max_tokens=800
    )
    
    full_text = response.choices[0].message.content
    
    # 3. Parse output
    talking_points = [line.strip() for line in full_text.split("\n") if line.strip().startswith("•")]
    confidence = "High" if "CONFIDENCE: High" in full_text else "Medium"
    
    return full_text, talking_points, target_price, confidence
```

---

## Testing & Debugging

### Manual API Testing

```bash
# Get all vendors
curl http://localhost:8000/api/v1/vendors

# Get all products
curl http://localhost:8000/api/v1/products

# Recommend vendors for product 1
curl -X POST http://localhost:8000/api/v1/ai/recommend-vendors \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 500,
    "top_n": 3
  }'

# Price analysis for vendor 2, product 1
curl http://localhost:8000/api/v1/ai/price-analysis/2/1

# Generate negotiation strategy
curl -X POST http://localhost:8000/api/v1/ai/negotiation-strategy \
  -H "Content-Type: application/json" \
  -d '{
    "vendor_id": 2,
    "product_id": 1,
    "quantity": 500,
    "current_quoted_price": 52.00,
    "target_price_reduction_pct": 12.0
  }'
```

### Seed Database Utilities

```bash
# Re-seed database (destructive)
cd backend
python seed_db.py --force

# Print price analysis table to console
python seed_db.py --stats

# Use custom CSV
python seed_db.py --csv /path/to/custom_data.csv
```

---

## Architecture Decisions & Trade-offs

| Decision | Why | Trade-off |
|----------|-----|-----------|
| **FAISS (in-memory)** | Zero infra, fast for 10 cases | Doesn't scale to 1M+ cases |
| **Sentence-Transformers local** | Privacy, no external API | Less semantic quality than GPT embeddings |
| **Explainable scoring** | Audit-friendly, reproducible | Less adaptive (fixed weights) |
| **PostgreSQL** | ACID, relational joins, cost | Overkill if data were truly NoSQL (unstructured) |
| **FastAPI** | Async, auto-docs, modern | Smaller ecosystem vs. Flask/Django |
| **React SPA** | Fast UX, client-side routing | Larger JS bundle (~200KB gzipped) |
| **Microservices** (backend + frontend + DB) | Independent scaling, separation of concerns | Added complexity, network latency |
| **Rule-based fallback** | Works without LLM key | Lower quality narratives; less adaptive |

---

## Summary for Interview

**ProcureAI is a full-stack GenAI procurement assistant that demonstrates:**

1. **Data Engineering:** CSV ingestion, schema design, relational modeling
2. **Backend Architecture:** FastAPI, SQLAlchemy ORM, RESTful API design
3. **ML/AI Integration:** Explainable scoring algorithms, FAISS-based RAG, LLM orchestration
4. **Frontend Development:** React SPA, Recharts visualization, API consumption
5. **DevOps:** Docker Compose, multi-service orchestration, deployment pipeline
6. **System Design:** Microservices, separation of concerns, scalability tradeoffs

**The core innovation:** RAG-grounded negotiation strategies. Instead of asking an LLM to hallucinate tactics, the system retrieves real historical cases via semantic search, then uses those as ground truth for the LLM's narrative generation.

**Why it matters for procurement:** Removes bias, adds data-driven decision-making, and creates audit trails. Procurement is highly regulated; explainability is a feature, not a limitation.
