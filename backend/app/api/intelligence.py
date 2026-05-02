from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.vendor_scoring import recommend_vendors
from app.services.price_analysis import analyse_price
from app.services.negotiation import generate_negotiation_strategy
from app.models.schemas import (
    VendorRecommendationRequest,
    VendorRecommendationResponse,
    PriceAnalysisResponse,
    NegotiationStrategyRequest,
    NegotiationStrategyResponse,
)

router = APIRouter(prefix="/ai", tags=["AI Intelligence"])


@router.post("/recommend-vendors", response_model=VendorRecommendationResponse)
def recommend(payload: VendorRecommendationRequest, db: Session = Depends(get_db)):
    """
    Score and rank vendors for a given product using explainable business rules.
    Returns top N vendors with full score breakdown.
    """
    result = recommend_vendors(db, payload.product_id, payload.quantity, payload.top_n or 3)
    if not result:
        raise HTTPException(status_code=404, detail="No data found for this product/vendor combination")
    return result


@router.get("/price-analysis/{vendor_id}/{product_id}", response_model=PriceAnalysisResponse)
def price_analysis(vendor_id: int, product_id: int, db: Session = Depends(get_db)):
    """
    Analyse historical pricing for a specific vendor × product combination.
    Returns deviation from market average, trend data, and negotiation leverage.
    """
    result = analyse_price(db, vendor_id, product_id)
    if not result:
        raise HTTPException(status_code=404, detail="No price data found")
    return result


@router.post("/negotiation-strategy", response_model=NegotiationStrategyResponse)
def negotiation_strategy(
    payload: NegotiationStrategyRequest, db: Session = Depends(get_db)
):
    """
    RAG-powered negotiation strategy generator.
    1. Performs price analysis
    2. Retrieves similar historical cases via FAISS semantic search
    3. Passes context to LLM for grounded strategy generation
    """
    result = generate_negotiation_strategy(db, payload)
    if not result:
        raise HTTPException(status_code=404, detail="Could not generate strategy — check vendor/product IDs")
    return result
