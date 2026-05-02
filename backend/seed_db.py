"""
Seed the database with realistic procurement data derived from:
  - Company Purchasing Dataset patterns
  - Online Retail dataset patterns

Run: python seed_db.py
"""
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.core.database import engine, Base, SessionLocal
from app.models.models import Vendor, Product, PurchaseOrder


VENDORS = [
    {"name": "GlobalTech Supplies", "category": "Electronics", "country": "China"},
    {"name": "EuroComponents GmbH", "category": "Electronics", "country": "Germany"},
    {"name": "PrimeParts Inc.", "category": "Industrial", "country": "USA"},
    {"name": "AsiaPacific Trading", "category": "Raw Materials", "country": "Singapore"},
    {"name": "NordSupply AB", "category": "Packaging", "country": "Sweden"},
    {"name": "MedSupplies Corp", "category": "Healthcare", "country": "USA"},
    {"name": "FastLog Freight", "category": "Logistics", "country": "Netherlands"},
]

PRODUCTS = [
    {"sku": "ELEC-001", "name": "Capacitor 100uF", "category": "Electronics", "unit": "piece"},
    {"sku": "ELEC-002", "name": "Resistor Pack 10k", "category": "Electronics", "unit": "pack"},
    {"sku": "IND-001", "name": "Aluminium Sheet 2mm", "category": "Industrial", "unit": "kg"},
    {"sku": "IND-002", "name": "Stainless Steel Rod", "category": "Industrial", "unit": "meter"},
    {"sku": "PKG-001", "name": "Cardboard Box A4", "category": "Packaging", "unit": "piece"},
    {"sku": "PKG-002", "name": "Bubble Wrap Roll", "category": "Packaging", "unit": "roll"},
    {"sku": "OFF-001", "name": "A4 Copy Paper", "category": "Office", "unit": "ream"},
]

DELIVERY_STATUSES = ["on_time", "on_time", "on_time", "late", "early"]


def random_date(start_days_ago: int = 365, end_days_ago: int = 0) -> datetime:
    delta = random.randint(end_days_ago, start_days_ago)
    return datetime.now() - timedelta(days=delta)


def seed():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        # Skip if already seeded
        if db.query(Vendor).count() > 0:
            print("Database already seeded. Skipping.")
            return

        # Insert vendors
        vendor_objs = []
        for v in VENDORS:
            vendor = Vendor(**v)
            db.add(vendor)
            vendor_objs.append(vendor)
        db.flush()

        # Insert products
        product_objs = []
        for p in PRODUCTS:
            product = Product(**p)
            db.add(product)
            product_objs.append(product)
        db.flush()

        # Generate purchase orders — each vendor × product with price variation
        BASE_PRICES = {
            "ELEC-001": 0.45, "ELEC-002": 2.10, "IND-001": 3.80,
            "IND-002": 8.50, "PKG-001": 0.35, "PKG-002": 12.00, "OFF-001": 4.50,
        }

        count = 0
        for product in product_objs:
            base_price = BASE_PRICES[product.sku]
            for vendor in vendor_objs:
                # Give each vendor a characteristic price offset (+/- 20%)
                vendor_offset = random.uniform(-0.20, 0.25)
                num_orders = random.randint(3, 12)

                for _ in range(num_orders):
                    # Add noise to simulate market variation
                    price_noise = random.uniform(-0.05, 0.05)
                    unit_price = round(base_price * (1 + vendor_offset + price_noise), 4)
                    quantity = random.choice([50, 100, 200, 500, 1000])
                    delivery_days = random.randint(2, 14)
                    delivery_status = random.choice(DELIVERY_STATUSES)
                    quality_rating = round(random.uniform(2.5, 5.0), 1)
                    order_date = random_date(730, 0)

                    order = PurchaseOrder(
                        vendor_id=vendor.id,
                        product_id=product.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        total_amount=round(unit_price * quantity, 2),
                        order_date=order_date,
                        delivery_days=delivery_days,
                        delivery_status=delivery_status,
                        quality_rating=quality_rating,
                    )
                    db.add(order)
                    count += 1

        db.commit()
        print(f"Seeded: {len(vendor_objs)} vendors, {len(product_objs)} products, {count} purchase orders.")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
