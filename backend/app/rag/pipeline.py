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
        "title": "Raw material 22% overpriced — leveraged competitor quote",
        "context": "Supplier quoted 22% above market for aluminium sheets. Procurement team cited two competitor prices and requested a price match within 3 business days or contract cancellation.",
        "product_category": "raw material",
        "price_deviation_pct": 22,
        "outcome": "15% reduction achieved. Supplier matched partial discount after escalation.",
        "tactics_used": ["competitor benchmarking", "walk-away threat", "deadline pressure"],
    },
    {
        "id": "case_002",
        "title": "Electronics component — volume discount negotiation",
        "context": "Vendor fairly priced but order volume tripled. Buyer negotiated a tiered volume discount: 5% at 500 units, 10% at 1000 units, 15% at 2000+ units.",
        "product_category": "electronics",
        "price_deviation_pct": 3,
        "outcome": "12% effective discount via volume tier. 18-month price lock secured.",
        "tactics_used": ["volume commitment", "price lock", "tiered pricing"],
    },
    {
        "id": "case_003",
        "title": "Office supplies — payment terms trade for discount",
        "context": "Vendor offered net-60 payment terms. Buyer offered net-15 in exchange for a 3% early payment discount.",
        "product_category": "office supplies",
        "price_deviation_pct": 0,
        "outcome": "3% discount secured through accelerated payment terms.",
        "tactics_used": ["early payment discount", "payment terms negotiation"],
    },
    {
        "id": "case_004",
        "title": "Industrial equipment — multi-year contract for price stability",
        "context": "Buyer committed to 3-year purchase agreement in exchange for capped annual price increases of 2%, significantly below market inflation.",
        "product_category": "industrial equipment",
        "price_deviation_pct": 8,
        "outcome": "Long-term price stability achieved. 8% savings over contract period vs spot pricing.",
        "tactics_used": ["long-term contract", "inflation cap", "volume guarantee"],
    },
    {
        "id": "case_005",
        "title": "Logistics services — total cost of ownership analysis",
        "context": "Vendor appeared cheapest on unit price but had 30% late delivery rate. Buyer modelled TCO including delays and presented analysis. Vendor improved SLA with penalty clauses.",
        "product_category": "logistics",
        "price_deviation_pct": -5,
        "outcome": "SLA penalties introduced. Effective cost reduced by 9% through fewer delays.",
        "tactics_used": ["TCO analysis", "SLA penalties", "delivery reliability data"],
    },
    {
        "id": "case_006",
        "title": "Packaging materials — reverse auction among 4 suppliers",
        "context": "Procurement ran a reverse auction with 4 pre-qualified suppliers. Final price 18% below initial quotes.",
        "product_category": "packaging",
        "price_deviation_pct": 18,
        "outcome": "18% reduction. New supplier onboarded. Existing supplier retained at competitive rate.",
        "tactics_used": ["reverse auction", "competitive bidding", "supplier diversification"],
    },
    {
        "id": "case_007",
        "title": "IT hardware — end-of-quarter timing leverage",
        "context": "Buyer deliberately delayed final PO to last week of vendor's fiscal quarter. Vendor eager to close deals for quota. Received 11% discount with no other concessions.",
        "product_category": "IT hardware",
        "price_deviation_pct": 11,
        "outcome": "11% discount. Accelerated delivery included at no extra charge.",
        "tactics_used": ["timing leverage", "fiscal quarter pressure", "urgency creation"],
    },
    {
        "id": "case_008",
        "title": "Chemical raw material — quality data in negotiation",
        "context": "Historical quality scores showed vendor at 3.1/5. Buyer presented defect rate data and requested quality improvement plan with price reduction until benchmark met.",
        "product_category": "chemical",
        "price_deviation_pct": 5,
        "outcome": "7% interim discount while quality improved. Bonus clause for sustained 4.5+ rating.",
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
