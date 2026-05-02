from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.models import Vendor, Product, PurchaseOrder
from app.models.schemas import (
    VendorCreate, VendorOut,
    ProductCreate, ProductOut,
    PurchaseOrderCreate, PurchaseOrderOut,
)

router = APIRouter()


# --- Vendors ---
@router.get("/vendors", response_model=List[VendorOut], tags=["Vendors"])
def list_vendors(db: Session = Depends(get_db)):
    return db.query(Vendor).all()


@router.post("/vendors", response_model=VendorOut, status_code=201, tags=["Vendors"])
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorOut, tags=["Vendors"])
def get_vendor(vendor_id: int, db: Session = Depends(get_db)):
    v = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return v


# --- Products ---
@router.get("/products", response_model=List[ProductOut], tags=["Products"])
def list_products(db: Session = Depends(get_db)):
    return db.query(Product).all()


@router.post("/products", response_model=ProductOut, status_code=201, tags=["Products"])
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


# --- Purchase Orders ---
@router.get("/orders", response_model=List[PurchaseOrderOut], tags=["Orders"])
def list_orders(
    vendor_id: int = None,
    product_id: int = None,
    db: Session = Depends(get_db),
):
    q = db.query(PurchaseOrder)
    if vendor_id:
        q = q.filter(PurchaseOrder.vendor_id == vendor_id)
    if product_id:
        q = q.filter(PurchaseOrder.product_id == product_id)
    return q.order_by(PurchaseOrder.order_date.desc()).all()


@router.post("/orders", response_model=PurchaseOrderOut, status_code=201, tags=["Orders"])
def create_order(payload: PurchaseOrderCreate, db: Session = Depends(get_db)):
    order = PurchaseOrder(
        **payload.model_dump(),
        total_amount=payload.unit_price * payload.quantity,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order
