"""
seed_db.py — Ingests spend_analysis_dataset.csv into PostgreSQL

Dataset columns:
  TransactionID, ItemName, Category, Quantity, UnitPrice,
  TotalCost, PurchaseDate, Supplier, Buyer

Mapping:
  Supplier  → vendors table
  ItemName  → products table (SKU = slugified name)
  Each row  → purchase_orders table

Derived fields (not in CSV — simulated realistically per supplier profile):
  delivery_days    → random, weighted by supplier reliability
  delivery_status  → on_time / late / early
  quality_rating   → 1–5, weighted by supplier profile

Usage:
  python seed_db.py                          # auto-finds CSV
  python seed_db.py --csv /path/to/file.csv
  python seed_db.py --stats                  # print price intelligence table
  python seed_db.py --force                  # drop all data and re-seed
"""

import argparse
import random
import os
import re

import pandas as pd
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import engine, Base, SessionLocal
from app.models.models import Vendor, Product, PurchaseOrder


# ---------------------------------------------------------------------------
# Supplier reliability profiles
# Derived from their position in the dataset (FurniWorks is the most expensive
# & slowest; QuickDeliver is fastest; CloudSoft has highest quality for Software)
# ---------------------------------------------------------------------------
SUPPLIER_PROFILES = {
    "TechMart Inc.":      {"avg_delivery": 5,  "on_time_rate": 0.88, "avg_quality": 4.3, "country": "USA"},
    "CloudSoft Corp.":    {"avg_delivery": 4,  "on_time_rate": 0.92, "avg_quality": 4.5, "country": "USA"},
    "OfficeSupplies Co.": {"avg_delivery": 7,  "on_time_rate": 0.80, "avg_quality": 3.8, "country": "UK"},
    "QuickDeliver Ltd.":  {"avg_delivery": 3,  "on_time_rate": 0.95, "avg_quality": 4.0, "country": "Singapore"},
    "FurniWorks Ltd.":    {"avg_delivery": 10, "on_time_rate": 0.65, "avg_quality": 3.4, "country": "China"},
}

CATEGORY_MAP = {
    "Electronics":     "Electronics",
    "Furniture":       "Furniture",
    "Stationery":      "Stationery",
    "Office Supplies": "Office Supplies",
    "Accessories":     "Accessories",
    "Software":        "Software",
}


def slugify(name: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", name.upper())[:6]


def derive_delivery(supplier_name: str) -> tuple:
    profile = SUPPLIER_PROFILES.get(supplier_name, {"avg_delivery": 7, "on_time_rate": 0.80})
    avg = profile["avg_delivery"]
    days = max(1, int(random.gauss(avg, avg * 0.4)))
    on_time = random.random() < profile["on_time_rate"]
    if on_time:
        status = "early" if days < avg - 1 else "on_time"
    else:
        status = "late"
    return days, status


def derive_quality(supplier_name: str) -> float:
    profile = SUPPLIER_PROFILES.get(supplier_name, {"avg_quality": 3.8})
    q = random.gauss(profile["avg_quality"], 0.4)
    return round(max(1.0, min(5.0, q)), 1)


def find_csv() -> str:
    candidates = [
        "./data/spend_analysis_dataset.csv",
        "./spend_analysis_dataset.csv",
        "/app/data/spend_analysis_dataset.csv",
        "/mnt/user-data/uploads/spend_analysis_dataset.csv",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(
        "Cannot find spend_analysis_dataset.csv.\n"
        "Either pass --csv /path/to/file or copy it to ./data/spend_analysis_dataset.csv"
    )


def seed(csv_path: str, force: bool = False):
    print(f"[seed] Reading: {csv_path}")
    df = pd.read_csv(csv_path)
    df["PurchaseDate"] = pd.to_datetime(df["PurchaseDate"])
    print(f"[seed] {len(df)} rows | {df['Supplier'].nunique()} suppliers | {df['ItemName'].nunique()} items")

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        if db.query(Vendor).count() > 0:
            if not force:
                print("[seed] Already seeded. Use --force to re-seed.")
                return
            # Truncate all tables
            db.execute(text("TRUNCATE purchase_orders, price_records RESTART IDENTITY CASCADE"))
            db.execute(text("TRUNCATE vendors RESTART IDENTITY CASCADE"))
            db.execute(text("TRUNCATE products RESTART IDENTITY CASCADE"))
            db.commit()
            print("[seed] Cleared existing data.")

        # --- Vendors ---
        vendor_map: dict = {}
        for name in df["Supplier"].unique():
            profile = SUPPLIER_PROFILES.get(name, {"country": "Unknown"})
            top_cat = df[df["Supplier"] == name]["Category"].mode()[0]
            v = Vendor(
                name=name,
                category=CATEGORY_MAP.get(top_cat, top_cat),
                country=profile["country"],
                contact_email=f"procurement@{re.sub(r'[^a-z0-9]', '', name.lower())}.com",
            )
            db.add(v)
            db.flush()
            vendor_map[name] = v.id
            print(f"  + Vendor: {name} (id={v.id})")

        # --- Products ---
        product_map: dict = {}
        sku_idx: dict = {}
        for item in df["ItemName"].unique():
            cat = df[df["ItemName"] == item]["Category"].mode()[0]
            slug = slugify(item)
            sku_idx[slug] = sku_idx.get(slug, 0) + 1
            sku = f"{slug}-{sku_idx[slug]:03d}"
            p = Product(
                sku=sku,
                name=item,
                category=CATEGORY_MAP.get(cat, cat),
                unit="piece",
            )
            db.add(p)
            db.flush()
            product_map[item] = p.id
            print(f"  + Product: {item} (sku={sku}, id={p.id})")

        # --- Purchase Orders ---
        count = 0
        for _, row in df.iterrows():
            vid = vendor_map.get(row["Supplier"])
            pid = product_map.get(row["ItemName"])
            if not vid or not pid:
                continue
            days, status = derive_delivery(row["Supplier"])
            quality = derive_quality(row["Supplier"])
            order = PurchaseOrder(
                vendor_id=vid,
                product_id=pid,
                quantity=float(row["Quantity"]),
                unit_price=float(row["UnitPrice"]),
                total_amount=float(row["TotalCost"]),
                order_date=row["PurchaseDate"].to_pydatetime(),
                delivery_days=days,
                delivery_status=status,
                quality_rating=quality,
                notes=f"Buyer: {row['Buyer']} | TxnID: {row['TransactionID']}",
            )
            db.add(order)
            count += 1

        db.commit()
        print(f"\n[seed] ✓ Inserted {len(vendor_map)} vendors, {len(product_map)} products, {count} orders.")

    except Exception as e:
        db.rollback()
        print(f"[seed] ERROR: {e}")
        raise
    finally:
        db.close()


def print_stats(csv_path: str):
    df = pd.read_csv(csv_path)
    market_avg = df.groupby("ItemName")["UnitPrice"].mean()
    supplier_avg = df.groupby(["Supplier", "ItemName"])["UnitPrice"].mean()

    print("\n=== Price Deviation by Supplier × Item ===")
    print(f"{'Supplier':<22} {'Item':<26} {'Supplier Avg':>13} {'Market Avg':>11} {'Deviation':>10}")
    print("-" * 88)
    for (supplier, item), s_avg in supplier_avg.items():
        m_avg = market_avg[item]
        dev = (s_avg - m_avg) / m_avg * 100
        flag = " ⚠ OVERPRICED" if dev > 10 else (" ✓ UNDERPRICED" if dev < -10 else "")
        print(f"{supplier:<22} {item:<26} ${s_avg:>12.2f} ${m_avg:>10.2f} {dev:>+9.1f}%{flag}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--stats", action="store_true")
    args = parser.parse_args()

    csv_path = args.csv or find_csv()

    if args.stats:
        print_stats(csv_path)
    else:
        seed(csv_path, force=args.force)
