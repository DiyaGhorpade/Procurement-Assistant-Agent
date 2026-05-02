from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Vendor Schemas ---
class VendorBase(BaseModel):
    name: str
    category: Optional[str] = None
    country: Optional[str] = None
    contact_email: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorOut(VendorBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Product Schemas ---
class ProductBase(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    unit: Optional[str] = "unit"


class ProductCreate(ProductBase):
    pass


class ProductOut(ProductBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# --- Purchase Order Schemas ---
class PurchaseOrderCreate(BaseModel):
    vendor_id: int
    product_id: int
    quantity: float
    unit_price: float
    delivery_days: Optional[int] = None
    delivery_status: Optional[str] = "on_time"
    quality_rating: Optional[float] = None
    notes: Optional[str] = None


class PurchaseOrderOut(PurchaseOrderCreate):
    id: int
    total_amount: float
    order_date: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# --- Vendor Scoring Schemas ---
class VendorScoreBreakdown(BaseModel):
    price_score: float
    delivery_score: float
    reliability_score: float
    total_score: float
    price_percentile: float
    avg_delivery_days: float
    on_time_rate: float
    avg_quality: float
    total_orders: int


class VendorRecommendation(BaseModel):
    vendor: VendorOut
    score_breakdown: VendorScoreBreakdown
    rank: int
    recommendation: str


class VendorRecommendationRequest(BaseModel):
    product_id: int
    quantity: float
    top_n: Optional[int] = 3


class VendorRecommendationResponse(BaseModel):
    product: ProductOut
    quantity: float
    recommendations: List[VendorRecommendation]
    analysis_note: str


# --- Price Analysis Schemas ---
class PriceTrend(BaseModel):
    period: str
    avg_price: float
    min_price: float
    max_price: float
    order_count: int


class PriceAnalysisResponse(BaseModel):
    vendor_id: int
    vendor_name: str
    product_id: int
    product_name: str
    current_market_avg: float
    vendor_avg_price: float
    price_deviation_pct: float
    price_status: str  # overpriced | fairly_priced | underpriced
    negotiation_leverage: str
    trend: List[PriceTrend]
    recommendation: str


# --- RAG / Negotiation Schemas ---
class NegotiationStrategyRequest(BaseModel):
    vendor_id: int
    product_id: int
    quantity: float
    current_quoted_price: float
    target_price_reduction_pct: Optional[float] = 10.0


class RetrievedCase(BaseModel):
    case_id: str
    title: str
    similarity_score: float
    outcome: str
    tactics_used: List[str]


class NegotiationStrategyResponse(BaseModel):
    vendor_name: str
    product_name: str
    price_analysis: PriceAnalysisResponse
    retrieved_cases: List[RetrievedCase]
    strategy: str
    key_talking_points: List[str]
    recommended_target_price: float
    confidence_level: str
