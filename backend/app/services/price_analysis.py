"""
Historical Price Intelligence Service

Analyses past pricing data to:
  - Detect if a vendor is overpriced / fairly priced / underpriced
  - Quantify negotiation leverage (% above/below market avg)
  - Produce monthly trend data
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import Optional

from app.models.models import PurchaseOrder, Vendor, Product
from app.models.schemas import PriceAnalysisResponse, PriceTrend


def _price_status(deviation_pct: float) -> tuple[str, str]:
    """Return (status_label, leverage_description)."""
    if deviation_pct > 10:
        return (
            "overpriced",
            f"Vendor is {deviation_pct:.1f}% above market average — strong leverage to negotiate.",
        )
    elif deviation_pct < -10:
        return (
            "underpriced",
            f"Vendor is {abs(deviation_pct):.1f}% below market average — lock in long-term contract.",
        )
    else:
        return (
            "fairly_priced",
            f"Vendor is within ±10% of market average ({deviation_pct:+.1f}%). "
            "Negotiate volume discounts or payment terms.",
        )


def analyse_price(
    db: Session,
    vendor_id: int,
    product_id: int,
) -> Optional[PriceAnalysisResponse]:
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    product = db.query(Product).filter(Product.id == product_id).first()
    if not vendor or not product:
        return None

    # Market average across all vendors
    market_avg_row = (
        db.query(func.avg(PurchaseOrder.unit_price))
        .filter(PurchaseOrder.product_id == product_id)
        .scalar()
    )
    if not market_avg_row:
        return None
    market_avg = round(float(market_avg_row), 4)

    # Vendor-specific average
    vendor_avg_row = (
        db.query(func.avg(PurchaseOrder.unit_price))
        .filter(
            PurchaseOrder.product_id == product_id,
            PurchaseOrder.vendor_id == vendor_id,
        )
        .scalar()
    )
    if not vendor_avg_row:
        return None
    vendor_avg = round(float(vendor_avg_row), 4)

    deviation_pct = round((vendor_avg - market_avg) / market_avg * 100, 2)
    price_status, leverage = _price_status(deviation_pct)

    # Monthly price trend for this vendor × product
    monthly_rows = (
        db.query(
            extract("year", PurchaseOrder.order_date).label("yr"),
            extract("month", PurchaseOrder.order_date).label("mo"),
            func.avg(PurchaseOrder.unit_price).label("avg_price"),
            func.min(PurchaseOrder.unit_price).label("min_price"),
            func.max(PurchaseOrder.unit_price).label("max_price"),
            func.count(PurchaseOrder.id).label("order_count"),
        )
        .filter(
            PurchaseOrder.product_id == product_id,
            PurchaseOrder.vendor_id == vendor_id,
        )
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )

    trend = []
    for r in monthly_rows:
        period = f"{int(r.yr)}-{int(r.mo):02d}"
        trend.append(
            PriceTrend(
                period=period,
                avg_price=round(r.avg_price, 4),
                min_price=round(r.min_price, 4),
                max_price=round(r.max_price, 4),
                order_count=r.order_count,
            )
        )

    # Human-readable recommendation
    if price_status == "overpriced":
        rec = (
            f"Cite market average of ${market_avg:.2f}. "
            f"Request a {min(deviation_pct, 20):.0f}% reduction to align with peer pricing."
        )
    elif price_status == "underpriced":
        rec = (
            "Price is competitive. Prioritise volume commitment or longer payment terms "
            "in exchange for a price-lock clause."
        )
    else:
        rec = (
            "Price is fair. Focus negotiations on delivery timelines, "
            "payment terms, or warranty conditions."
        )

    return PriceAnalysisResponse(
        vendor_id=vendor_id,
        vendor_name=vendor.name,
        product_id=product_id,
        product_name=product.name,
        current_market_avg=market_avg,
        vendor_avg_price=vendor_avg,
        price_deviation_pct=deviation_pct,
        price_status=price_status,
        negotiation_leverage=leverage,
        trend=trend,
        recommendation=rec,
    )
