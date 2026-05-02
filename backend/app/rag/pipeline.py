"""
RAG-Based Negotiation Strategy Generator

Pipeline:
  1. Load negotiation case corpus and build FAISS index (on startup)
  2. Embed query (vendor + product + price context)
  3. Retrieve top-k similar historical cases via FAISS
  4. Inject retrieved cases into LLM prompt
  5. LLM generates a grounded negotiation strategy

Design decisions:
  - FAISS is in-memory (fast, no infra). Swap for Pinecone/Weaviate in prod.
  - Sentence-Transformers runs locally — no external calls for embeddings.
  - LLM is called LAST and only for generation, never for retrieval decisions.
"""
import json
import os
import numpy as np
import faiss
from pathlib import Path
from typing import List, Optional
from sentence_transformers import SentenceTransformer
from openai import OpenAI

from app.core.config import settings
from app.models.schemas import RetrievedCase


# ---------------------------------------------------------------------------
# Corpus — in production this would be loaded from a real database/file
# ---------------------------------------------------------------------------
BUILT_IN_CASES = [
    {
        "id": "case_001",
        "title": "Laptop overpriced 22% — leveraged competitor quote to get reduction",
        "context": "Supplier quoted laptops 22% above market average. Procurement presented two competitor prices and requested price match within 5 business days or threatened to switch suppliers.",
        "product_category": "electronics laptop monitor",
        "price_deviation_pct": 22,
        "outcome": "15% reduction achieved. Supplier matched partial discount after escalation.",
        "tactics_used": ["competitor benchmarking", "walk-away threat", "deadline pressure"],
    },
    {
        "id": "case_002",
        "title": "Electronics bulk order — volume discount negotiation for monitors",
        "context": "Vendor fairly priced on monitors but order volume increased 3x. Buyer negotiated tiered volume discount: 5% at 10 units, 10% at 20 units, 15% at 50+ units.",
        "product_category": "electronics monitor printer",
        "price_deviation_pct": 3,
        "outcome": "12% effective discount via volume tier. 12-month price lock secured.",
        "tactics_used": ["volume commitment", "price lock", "tiered pricing"],
    },
    {
        "id": "case_003",
        "title": "Printer ink overpriced — market data presented, SLA added",
        "context": "Office supplies vendor priced printer ink 18% above market. Historical data showed 3 cheaper alternatives. Buyer presented analysis and requested 15% reduction plus guaranteed 3-day delivery.",
        "product_category": "electronics printer ink office supplies",
        "price_deviation_pct": 18,
        "outcome": "14% price reduction achieved. Delivery SLA of 3 days included at no extra cost.",
        "tactics_used": ["market data presentation", "alternative supplier threat", "SLA bundling"],
    },
    {
        "id": "case_004",
        "title": "Annual software license — multi-year commitment for price stability",
        "context": "Vendor quoted annual software license 25% above previous year. Buyer offered 3-year commitment in exchange for capped annual increases of 3% and no mid-term price hikes.",
        "product_category": "software annual license",
        "price_deviation_pct": 25,
        "outcome": "Initial quote reduced by 18%. 3-year price cap agreed. Includes free user seats.",
        "tactics_used": ["multi-year commitment", "inflation cap", "seat bundling"],
    },
    {
        "id": "case_005",
        "title": "Software license end-of-quarter timing — fiscal pressure discount",
        "context": "Buyer delayed signing annual software license to last week of vendor's fiscal quarter. Vendor eager to close deals. Received 11% discount with no other concessions.",
        "product_category": "software license annual",
        "price_deviation_pct": 11,
        "outcome": "11% discount. Additional user licences added at no charge.",
        "tactics_used": ["timing leverage", "fiscal quarter pressure", "urgency creation"],
    },
    {
        "id": "case_006",
        "title": "Desk chairs — FurniWorks overpriced, reverse auction run",
        "context": "FurniWorks Ltd. quoted desk chairs 20% above market. Procurement ran a reverse auction among 3 pre-qualified suppliers. Final price 17% below initial quote.",
        "product_category": "furniture desk chair",
        "price_deviation_pct": 20,
        "outcome": "17% reduction. New supplier onboarded. FurniWorks retained at competitive rate.",
        "tactics_used": ["reverse auction", "competitive bidding", "supplier diversification"],
    },
    {
        "id": "case_007",
        "title": "Furniture — total cost of ownership analysis including delays",
        "context": "Vendor appeared cheapest on unit price but had 35% late delivery rate. Buyer modelled TCO including delay costs and presented it. Vendor improved delivery SLA with penalty clauses.",
        "product_category": "furniture whiteboard desk",
        "price_deviation_pct": -5,
        "outcome": "SLA penalties introduced. Effective cost reduced 9% through fewer operational delays.",
        "tactics_used": ["TCO analysis", "SLA penalties", "delivery reliability data"],
    },
    {
        "id": "case_008",
        "title": "Office supplies — payment terms trade for discount",
        "context": "Vendor offered net-60 payment terms on office supplies. Buyer offered net-15 early payment in exchange for a 4% discount on all orders.",
        "product_category": "office supplies stationery notepad stapler",
        "price_deviation_pct": 0,
        "outcome": "4% discount secured through early payment terms across all office supply orders.",
        "tactics_used": ["early payment discount", "payment terms negotiation"],
    },
    {
        "id": "case_009",
        "title": "Stationery — consolidated supplier for across-the-board discount",
        "context": "Company was buying stationery from 3 suppliers. Consolidated all spend to single supplier in exchange for 8% blanket discount and priority processing.",
        "product_category": "stationery notepad stapler office supplies",
        "price_deviation_pct": 8,
        "outcome": "8% discount achieved. Reduced procurement admin by 60%.",
        "tactics_used": ["spend consolidation", "single supplier deal", "volume guarantee"],
    },
    {
        "id": "case_010",
        "title": "Laptop bags — quality data used to negotiate price reduction",
        "context": "Historical quality scores showed supplier at 3.0/5 for laptop bags. Buyer presented defect rate and return data, requested price reduction until quality benchmark of 4.0 was met.",
        "product_category": "accessories laptop bag",
        "price_deviation_pct": 5,
        "outcome": "7% interim discount while quality improved. Penalty clause for sustained poor quality.",
        "tactics_used": ["quality data", "performance benchmarking", "conditional pricing"],
    },
]

class RAGPipeline:
    def __init__(self):
        self.model: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatIP] = None
        self.cases: List[dict] = []
        self.llm_client: Optional[OpenAI] = None

    def initialise(self):
        """Load embedding model, build FAISS index, init LLM client."""
        print("[RAG] Loading embedding model...")
        self.model = SentenceTransformer(settings.EMBEDDING_MODEL)

        # Load cases from file if exists, otherwise use built-ins
        cases_path = Path(settings.NEGOTIATION_CASES_PATH)
        if cases_path.exists():
            with open(cases_path) as f:
                self.cases = json.load(f)
        else:
            self.cases = BUILT_IN_CASES

        # Build FAISS index (inner-product on L2-normalised vectors = cosine sim)
        corpus_texts = [
            f"{c['title']} {c['context']} {c['product_category']}"
            for c in self.cases
        ]
        embeddings = self.model.encode(corpus_texts, normalize_embeddings=True)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings.astype("float32"))
        print(f"[RAG] FAISS index built with {len(self.cases)} cases (dim={dim})")

        # LLM client
        if settings.OPENAI_API_KEY:
            self.llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            print("[RAG] LLM client initialised (OpenAI)")

    def retrieve(self, query: str, top_k: int = 3) -> List[RetrievedCase]:
        """Embed query and retrieve top-k similar cases from FAISS."""
        if not self.model or not self.index:
            return []

        q_vec = self.model.encode([query], normalize_embeddings=True).astype("float32")
        scores, indices = self.index.search(q_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            case = self.cases[idx]
            results.append(
                RetrievedCase(
                    case_id=case["id"],
                    title=case["title"],
                    similarity_score=round(float(score), 4),
                    outcome=case["outcome"],
                    tactics_used=case["tactics_used"],
                )
            )
        return results

    def generate_strategy(
        self,
        vendor_name: str,
        product_name: str,
        quantity: float,
        quoted_price: float,
        market_avg: float,
        deviation_pct: float,
        price_status: str,
        retrieved_cases: List[RetrievedCase],
        target_reduction_pct: float = 10.0,
    ) -> tuple[str, List[str], float, str]:
        """
        Returns: (strategy_text, talking_points, recommended_target_price, confidence)
        """
        target_price = round(quoted_price * (1 - target_reduction_pct / 100), 2)

        cases_context = "\n".join(
            [
                f"- [{c.case_id}] {c.title}\n"
                f"  Tactics: {', '.join(c.tactics_used)}\n"
                f"  Outcome: {c.outcome}"
                for c in retrieved_cases
            ]
        )

        system_prompt = """You are an expert procurement negotiation advisor. 
Your role is to generate actionable, grounded negotiation strategies based on real historical data.
Always be specific, professional, and data-driven. 
Output format: 
1. A strategic narrative (3-4 paragraphs)
2. Key talking points (bulleted list, prefix each with "•")
3. End with: CONFIDENCE: [Low|Medium|High]"""

        user_prompt = f"""Generate a negotiation strategy for the following procurement scenario:

VENDOR: {vendor_name}
PRODUCT: {product_name}
QUANTITY: {quantity:,.0f} units
QUOTED PRICE: ${quoted_price:.2f}/unit
MARKET AVERAGE: ${market_avg:.2f}/unit
VENDOR vs MARKET: {deviation_pct:+.1f}% ({price_status})
TARGET PRICE: ${target_price:.2f}/unit (reduce by {target_reduction_pct:.0f}%)

SIMILAR HISTORICAL CASES (retrieved via semantic search):
{cases_context}

Generate a negotiation strategy grounded in the above data and historical cases.
Include specific tactics that worked in similar scenarios."""

        if self.llm_client:
            response = self.llm_client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=800,
            )
            full_text = response.choices[0].message.content
        else:
            # Fallback: rule-based strategy when no LLM key
            full_text = self._rule_based_strategy(
                vendor_name, product_name, quoted_price, market_avg,
                deviation_pct, price_status, retrieved_cases, target_price,
            )

        # Parse talking points from the LLM output
        talking_points = []
        for line in full_text.split("\n"):
            if line.strip().startswith("•"):
                talking_points.append(line.strip().lstrip("• ").strip())

        # Parse confidence
        confidence = "Medium"
        if "CONFIDENCE: High" in full_text:
            confidence = "High"
        elif "CONFIDENCE: Low" in full_text:
            confidence = "Low"

        # Clean strategy text (remove the parsed sections for cleanliness)
        strategy = full_text.replace("CONFIDENCE: High", "").replace(
            "CONFIDENCE: Medium", ""
        ).replace("CONFIDENCE: Low", "").strip()

        return strategy, talking_points, target_price, confidence

    def _rule_based_strategy(
        self,
        vendor_name, product_name, quoted_price, market_avg,
        deviation_pct, price_status, retrieved_cases, target_price,
    ) -> str:
        """Fallback strategy when LLM is unavailable."""
        tactics = []
        for c in retrieved_cases:
            tactics.extend(c.tactics_used)
        tactics_str = ", ".join(set(tactics[:5]))

        if price_status == "overpriced":
            return (
                f"**Opening Position:** {vendor_name} is quoting ${quoted_price:.2f}/unit, "
                f"which is {deviation_pct:.1f}% above the market average of ${market_avg:.2f}. "
                f"This gives you strong leverage to negotiate.\n\n"
                f"**Strategy:** Present the market benchmark data directly. Request alignment "
                f"to the market average or provide competitor quotes to justify your position. "
                f"Based on similar historical cases, tactics like {tactics_str} have worked well.\n\n"
                f"**Target:** Push for ${target_price:.2f}/unit. "
                f"Be prepared to walk away or invite competing bids if the vendor does not move.\n\n"
                f"• Cite market average of ${market_avg:.2f} as your opening data point\n"
                f"• Request price match or written justification for premium\n"
                f"• Offer extended payment terms in exchange for immediate price reduction\n"
                f"• Set a 5-business-day deadline for revised quote\n"
                f"CONFIDENCE: High"
            )
        else:
            return (
                f"**Strategic Context:** {vendor_name} is fairly/competitively priced "
                f"at {deviation_pct:+.1f}% vs market. Shift focus to non-price terms.\n\n"
                f"**Strategy:** Leverage volume commitment, payment terms, or delivery SLAs "
                f"to extract additional value without pressuring on price alone. "
                f"Historical cases suggest: {tactics_str}.\n\n"
                f"• Negotiate volume-based discounts for {quoted_price:.0f}+ unit orders\n"
                f"• Request early payment discount (net-15 vs net-60)\n"
                f"• Propose multi-year price stability clause\n"
                f"• Include delivery SLA penalties to protect reliability\n"
                f"CONFIDENCE: Medium"
            )


# Global singleton — initialised once on app startup
rag_pipeline = RAGPipeline()
