from sqlalchemy.orm import Session
from typing import Optional

from app.rag.pipeline import rag_pipeline
from app.services.price_analysis import analyse_price
from app.models.models import Vendor, Product
from app.models.schemas import NegotiationStrategyResponse, NegotiationStrategyRequest


def generate_negotiation_strategy(
    db: Session,
    req: NegotiationStrategyRequest,
) -> Optional[NegotiationStrategyResponse]:
    vendor = db.query(Vendor).filter(Vendor.id == req.vendor_id).first()
    product = db.query(Product).filter(Product.id == req.product_id).first()
    if not vendor or not product:
        return None

    # Step 1: Price analysis
    price_analysis = analyse_price(db, req.vendor_id, req.product_id)
    if not price_analysis:
        return None

    # Step 2: RAG retrieval — build rich query for semantic search
    rag_query = (
        f"{price_analysis.price_status} vendor {product.category or product.name} "
        f"price {price_analysis.price_deviation_pct:+.0f}% deviation negotiation "
        f"quantity {req.quantity:.0f}"
    )
    retrieved_cases = rag_pipeline.retrieve(rag_query, top_k=3)

    # Step 3: LLM strategy generation (grounded in retrieved cases)
    strategy, talking_points, target_price, confidence = rag_pipeline.generate_strategy(
        vendor_name=vendor.name,
        product_name=product.name,
        quantity=req.quantity,
        quoted_price=req.current_quoted_price,
        market_avg=price_analysis.current_market_avg,
        deviation_pct=price_analysis.price_deviation_pct,
        price_status=price_analysis.price_status,
        retrieved_cases=retrieved_cases,
        target_reduction_pct=req.target_price_reduction_pct,
    )

    return NegotiationStrategyResponse(
        vendor_name=vendor.name,
        product_name=product.name,
        price_analysis=price_analysis,
        retrieved_cases=retrieved_cases,
        strategy=strategy,
        key_talking_points=talking_points,
        recommended_target_price=target_price,
        confidence_level=confidence,
    )
