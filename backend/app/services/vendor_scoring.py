"""
Vendor Recommendation Engine
Scores vendors using explainable business rules across three dimensions:
  - Price Score     (40%): Lower price relative to peers → higher score
  - Delivery Score  (30%): Faster delivery → higher score
  - Reliability     (30%): On-time rate × quality rating
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from typing import List, Optional
import numpy as np

from app.models.models import Vendor, PurchaseOrder, Product
from app.models.schemas import (
    VendorScoreBreakdown,
    VendorRecommendation,
    VendorRecommendationResponse,
)


WEIGHT_PRICE = 0.40
WEIGHT_DELIVERY = 0.30
WEIGHT_RELIABILITY = 0.30


def _safe_pct_rank(value: float, all_values: List[float]) -> float:
    """Return percentile rank (0-100). Lower price → higher rank."""
    if not all_values or len(all_values) == 1:
        return 50.0
    arr = np.array(all_values)
    pct = (arr < value).sum() / len(arr) * 100
    return round(float(pct), 2)


def get_vendor_stats(db: Session, product_id: int) -> List[dict]:
    """Aggregate historical stats per vendor for a given product."""
    rows = (
        db.query(
            PurchaseOrder.vendor_id,
            func.avg(PurchaseOrder.unit_price).label("avg_price"),
            func.avg(PurchaseOrder.delivery_days).label("avg_delivery"),
            func.count(PurchaseOrder.id).label("total_orders"),
            func.avg(PurchaseOrder.quality_rating).label("avg_quality"),
            func.sum(
                case((PurchaseOrder.delivery_status == "on_time", 1), else_=0)
            ).label("on_time_count"),
        )
        .filter(PurchaseOrder.product_id == product_id)
        .group_by(PurchaseOrder.vendor_id)
        .all()
    )

    stats = []
    for r in rows:
        on_time_rate = (r.on_time_count / r.total_orders * 100) if r.total_orders else 0
        stats.append(
    {
        "vendor_id": r.vendor_id,
        "avg_price": float(round(r.avg_price or 0, 4)),
        "avg_delivery": float(round(r.avg_delivery or 7, 1)),
        "total_orders": r.total_orders,
        "avg_quality": float(round(r.avg_quality or 3.0, 2)),
        "on_time_rate": float(round(on_time_rate, 2)),
    }
)
    return stats


def score_vendors(stats: List[dict]) -> List[dict]:
    """Compute normalised scores (0-100) for each vendor."""
    if not stats:
        return []

    prices = [s["avg_price"] for s in stats]
    deliveries = [s["avg_delivery"] for s in stats]

    min_price, max_price = min(prices), max(prices)
    min_del, max_del = min(deliveries), max(deliveries)

    scored = []
    for s in stats:
        # Price score: lower is better → invert range
        if max_price == min_price:
            price_score = 100.0
        else:
            price_score = (1 - (s["avg_price"] - min_price) / (max_price - min_price)) * 100

        # Delivery score: fewer days is better
        if max_del == min_del:
            delivery_score = 100.0
        else:
            delivery_score = (1 - (s["avg_delivery"] - min_del) / (max_del - min_del)) * 100

        # Reliability: on-time rate (0-100) weighted with quality (0-5 → 0-100)
        quality_score = (s["avg_quality"] / 5.0) * 100 if s["avg_quality"] else 50.0
        reliability_score = 0.6 * s["on_time_rate"] + 0.4 * quality_score

        total_score = (
            WEIGHT_PRICE * price_score
            + WEIGHT_DELIVERY * delivery_score
            + WEIGHT_RELIABILITY * reliability_score
        )

        price_pct = _safe_pct_rank(s["avg_price"], prices)

        scored.append(
            {
                **s,
                "price_score": round(price_score, 2),
                "delivery_score": round(delivery_score, 2),
                "reliability_score": round(reliability_score, 2),
                "total_score": round(total_score, 2),
                "price_percentile": round(price_pct, 2),
            }
        )

    return sorted(scored, key=lambda x: x["total_score"], reverse=True)


def _recommendation_text(rank: int, score: float, on_time_rate: float) -> str:
    if rank == 1 and score >= 70:
        return "Top pick. Strongest overall performance across price, delivery and reliability."
    if score >= 55:
        return "Strong alternative. Consider if primary vendor is unavailable."
    if on_time_rate < 60:
        return "Caution: low on-time rate. Suitable only for non-critical purchases."
    return "Below-average performer. Use only when other options are exhausted."


def recommend_vendors(
    db: Session,
    product_id: int,
    quantity: float,
    top_n: int = 3,
) -> Optional[VendorRecommendationResponse]:
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    stats = get_vendor_stats(db, product_id)
    if not stats:
        return None

    scored = score_vendors(stats)

    recommendations: List[VendorRecommendation] = []
    for rank, s in enumerate(scored[:top_n], start=1):
        vendor = db.query(Vendor).filter(Vendor.id == s["vendor_id"]).first()
        if not vendor:
            continue

        breakdown = VendorScoreBreakdown(
            price_score=s["price_score"],
            delivery_score=s["delivery_score"],
            reliability_score=s["reliability_score"],
            total_score=s["total_score"],
            price_percentile=s["price_percentile"],
            avg_delivery_days=s["avg_delivery"],
            on_time_rate=s["on_time_rate"],
            avg_quality=s["avg_quality"],
            total_orders=s["total_orders"],
        )
        recommendations.append(
            VendorRecommendation(
                vendor=vendor,
                score_breakdown=breakdown,
                rank=rank,
                recommendation=_recommendation_text(rank, s["total_score"], s["on_time_rate"]),
            )
        )

    note = (
        f"Scored {len(scored)} vendors with historical data for '{product.name}'. "
        f"Weights: Price {int(WEIGHT_PRICE*100)}%, Delivery {int(WEIGHT_DELIVERY*100)}%, "
        f"Reliability {int(WEIGHT_RELIABILITY*100)}%."
    )

    return VendorRecommendationResponse(
        product=product,
        quantity=quantity,
        recommendations=recommendations,
        analysis_note=note,
    )
