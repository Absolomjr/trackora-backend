#!/usr/bin/env python
"""
Trackora seed script — populates the store with realistic hardware data via the API.

It is IDEMPOTENT and safe to re-run:
  * Categories / suppliers / products / customers are matched by a natural key
    (name or SKU) and only created if missing — so your existing categories are reused.
  * Stock-in is only applied to products that currently have quantity 0
    (so re-running won't keep adding stock).
  * Sample orders + stock-out run only if there are no orders yet (a fresh seed).

Usage:
    python seed_data.py
    python seed_data.py --base-url http://localhost:8000 --email admin@trackora.com --password "Admin12345!"

Environment variables (used as defaults):
    TRACKORA_API_URL, TRACKORA_ADMIN_EMAIL, TRACKORA_ADMIN_PASSWORD

Requires only the Python standard library and a running backend with an admin account.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
CATEGORIES = [
    ("Cement", "Building cement, all brands"),
    ("Iron Sheets", "Roofing iron sheets"),
    ("Paint", "Interior & exterior paints"),
    ("Pipes", "PVC and PPR piping"),
    ("Tiles", "Floor and wall tiles"),
    ("Nails & Fasteners", "Nails, screws, bolts"),
    ("Electrical Cables", "Wiring cables"),
    ("Plumbing", "Valves, fittings, joints"),
    ("Tools", "Hand tools & equipment"),
]

SUPPLIERS = [
    {"name": "Hima Cement Ltd", "contact_person": "Robert Aine", "phone": "0312 200100", "email": "sales@hima.co.ug", "address": "Kampala"},
    {"name": "Tororo Cement Company Ltd", "contact_person": "Grace Apio", "phone": "0414 345600", "email": "orders@tororocement.com", "address": "Tororo"},
    {"name": "Roofings Group", "contact_person": "Peter Okwir", "phone": "0312 233444", "email": "info@roofings.co.ug", "address": "Lubowa, Kampala"},
    {"name": "Uganda Baati Ltd", "contact_person": "Mary Adeke", "phone": "0417 718000", "email": "sales@ugandabaati.com", "address": "Industrial Area, Kampala"},
    {"name": "Sadolin Paints Uganda", "contact_person": "Joseph Mwesigwa", "phone": "0414 251400", "email": "care@sadolin.co.ug", "address": "Kampala"},
    {"name": "Nice House of Plastics", "contact_person": "Hassan Lubega", "phone": "0414 567200", "email": "sales@nice.co.ug", "address": "Kampala"},
    {"name": "East African Cables Ltd", "contact_person": "Daniel Otim", "phone": "0312 260700", "email": "sales@eacables.co.ug", "address": "Industrial Area, Kampala"},
    {"name": "Hardware World Ltd", "contact_person": "Sam Kato", "phone": "0772 808090", "email": "hardwareworld@gmail.com", "address": "Kisenyi, Kampala"},
]

# category, supplier, unit, cost_price, selling_price, reorder_level, initial_qty
PRODUCTS = [
    {"name": "Hima Cement 50kg", "sku": "CEM-001", "category": "Cement", "supplier": "Hima Cement Ltd", "unit": "bag", "cost_price": "28000", "selling_price": "33000", "reorder_level": 20, "initial_qty": 120},
    {"name": "Tororo Cement 50kg", "sku": "CEM-002", "category": "Cement", "supplier": "Tororo Cement Company Ltd", "unit": "bag", "cost_price": "27000", "selling_price": "32000", "reorder_level": 20, "initial_qty": 100},
    {"name": "Gauge 30 Iron Sheet 3m", "sku": "IRS-001", "category": "Iron Sheets", "supplier": "Roofings Group", "unit": "sheet", "cost_price": "38000", "selling_price": "45000", "reorder_level": 15, "initial_qty": 60},
    {"name": "Gauge 28 Iron Sheet 3m", "sku": "IRS-002", "category": "Iron Sheets", "supplier": "Uganda Baati Ltd", "unit": "sheet", "cost_price": "52000", "selling_price": "60000", "reorder_level": 15, "initial_qty": 50},
    {"name": "Sadolin Super Gloss White 4L", "sku": "PNT-001", "category": "Paint", "supplier": "Sadolin Paints Uganda", "unit": "piece", "cost_price": "45000", "selling_price": "55000", "reorder_level": 10, "initial_qty": 40},
    {"name": "Sadolin Matt Emulsion 20L", "sku": "PNT-002", "category": "Paint", "supplier": "Sadolin Paints Uganda", "unit": "piece", "cost_price": "120000", "selling_price": "145000", "reorder_level": 8, "initial_qty": 25},
    {"name": "PVC Pipe 1\" x 6m", "sku": "PIP-001", "category": "Pipes", "supplier": "Nice House of Plastics", "unit": "piece", "cost_price": "12000", "selling_price": "16000", "reorder_level": 25, "initial_qty": 150},
    {"name": "PPR Pipe 20mm x 4m", "sku": "PIP-002", "category": "Pipes", "supplier": "Nice House of Plastics", "unit": "piece", "cost_price": "9000", "selling_price": "13000", "reorder_level": 25, "initial_qty": 120},
    {"name": "Ceramic Floor Tile 60x60 (carton)", "sku": "TIL-001", "category": "Tiles", "supplier": "Hardware World Ltd", "unit": "box", "cost_price": "35000", "selling_price": "45000", "reorder_level": 20, "initial_qty": 80},
    {"name": "Wall Tile 30x60 (carton)", "sku": "TIL-002", "category": "Tiles", "supplier": "Hardware World Ltd", "unit": "box", "cost_price": "28000", "selling_price": "38000", "reorder_level": 20, "initial_qty": 70},
    {"name": "Wire Nails 3 inch", "sku": "NAL-001", "category": "Nails & Fasteners", "supplier": "Hardware World Ltd", "unit": "kg", "cost_price": "5000", "selling_price": "7000", "reorder_level": 50, "initial_qty": 120},
    {"name": "Roofing Nails 2.5 inch", "sku": "NAL-002", "category": "Nails & Fasteners", "supplier": "Roofings Group", "unit": "kg", "cost_price": "6000", "selling_price": "8500", "reorder_level": 50, "initial_qty": 80},
    {"name": "Twin & Earth Cable 1.5mm (100m)", "sku": "CAB-001", "category": "Electrical Cables", "supplier": "East African Cables Ltd", "unit": "roll", "cost_price": "150000", "selling_price": "180000", "reorder_level": 10, "initial_qty": 30},
    {"name": "Single Core Cable 2.5mm (100m)", "sku": "CAB-002", "category": "Electrical Cables", "supplier": "East African Cables Ltd", "unit": "roll", "cost_price": "210000", "selling_price": "250000", "reorder_level": 10, "initial_qty": 20},
    {"name": "Gate Valve 1\"", "sku": "PLM-001", "category": "Plumbing", "supplier": "Nice House of Plastics", "unit": "piece", "cost_price": "15000", "selling_price": "20000", "reorder_level": 15, "initial_qty": 40},
    {"name": "PVC Elbow 1\"", "sku": "PLM-002", "category": "Plumbing", "supplier": "Nice House of Plastics", "unit": "piece", "cost_price": "1500", "selling_price": "2500", "reorder_level": 100, "initial_qty": 500},
    {"name": "Claw Hammer", "sku": "TOOL-001", "category": "Tools", "supplier": "Hardware World Ltd", "unit": "piece", "cost_price": "12000", "selling_price": "18000", "reorder_level": 10, "initial_qty": 25},
    {"name": "Wheelbarrow", "sku": "TOOL-002", "category": "Tools", "supplier": "Hardware World Ltd", "unit": "piece", "cost_price": "95000", "selling_price": "120000", "reorder_level": 5, "initial_qty": 12},
]

CUSTOMERS = [
    {"name": "John Okello", "phone": "0772 123456", "email": "john.okello@gmail.com", "address": "Nakawa, Kampala"},
    {"name": "Sarah Nakato", "phone": "0701 987654", "email": "sarahn@gmail.com", "address": "Ntinda, Kampala"},
    {"name": "Kampala Builders Ltd", "phone": "0414 200300", "email": "procurement@kbuilders.co.ug", "address": "Industrial Area, Kampala"},
    {"name": "Mukasa Construction Co", "phone": "0772 555888", "email": "mukasaconstruction@gmail.com", "address": "Mukono"},
    {"name": "Najjera Hardware Retailers", "phone": "0758 334455", "email": "najjerahardware@gmail.com", "address": "Najjera, Wakiso"},
]

# customer (by name or None for walk-in), payment_method, discount, items [(sku, qty)]
ORDERS = [
    {"customer": "John Okello", "payment_method": "cash", "discount": "0",
     "items": [("CEM-001", 5), ("IRS-001", 2)]},
    {"customer": "Kampala Builders Ltd", "payment_method": "bank", "discount": "20000",
     "items": [("CEM-001", 50), ("IRS-002", 20), ("PLM-002", 100)]},
    {"customer": None, "payment_method": "mobile", "discount": "0",
     "items": [("PNT-001", 1), ("NAL-001", 3), ("TOOL-001", 1)]},
]

STOCK_OUTS = [
    {"reason": "damage", "note": "2 tile cartons broke in storage", "items": [("TIL-002", 2)]},
]


# ---------------------------------------------------------------------------
# Tiny HTTP helper (stdlib only)
# ---------------------------------------------------------------------------
class Api:
    def __init__(self, base_url, token=None):
        self.base = base_url.rstrip("/")
        self.token = token

    def _request(self, method, path, data=None):
        url = self.base + path if path.startswith("/") else path
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req) as resp:
                raw = resp.read().decode()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode()
            try:
                parsed = json.loads(raw)
            except ValueError:
                parsed = raw
            return exc.code, parsed
        except urllib.error.URLError as exc:
            print(f"\nERROR: could not reach {url} — {exc.reason}")
            print("Is the backend running? Try: python manage.py runserver")
            sys.exit(1)

    def get(self, path):
        return self._request("GET", path)

    def post(self, path, data):
        return self._request("POST", path, data)

    def fetch_all(self, path):
        """Follow DRF pagination and return a flat list of results."""
        results = []
        url = self.base + path
        while url:
            status, data = self._request("GET", url)
            if status != 200:
                raise SystemExit(f"GET {url} failed: {status} {data}")
            if isinstance(data, dict) and "results" in data:
                results.extend(data["results"])
                url = data.get("next")
            elif isinstance(data, list):
                results.extend(data)
                url = None
            else:
                results.append(data)
                url = None
        return results


# ---------------------------------------------------------------------------
# Seeding steps
# ---------------------------------------------------------------------------
def ensure(api, path, items, key_field, key_of_item, build_payload, label):
    """
    Generic get-or-create. Returns a dict mapping natural-key -> object.
    `items` is the desired data; `key_of_item(item)` and the API object's
    `key_field` are compared to decide existence.
    """
    existing = {obj[key_field]: obj for obj in api.fetch_all(path)}
    result = {}
    created = 0
    for item in items:
        key = key_of_item(item)
        if key in existing:
            result[key] = existing[key]
        else:
            status, data = api.post(path, build_payload(item))
            if status not in (200, 201):
                raise SystemExit(f"  ! failed to create {label} '{key}': {status} {data}")
            result[key] = data
            existing[key] = data
            created += 1
    print(f"  {label}: {created} created, {len(items) - created} already existed")
    return result


def main():
    parser = argparse.ArgumentParser(description="Seed Trackora with hardware-store data.")
    parser.add_argument("--base-url", default=os.getenv("TRACKORA_API_URL", "http://localhost:8000"))
    parser.add_argument("--email", default=os.getenv("TRACKORA_ADMIN_EMAIL", "admin@trackora.com"))
    parser.add_argument("--password", default=os.getenv("TRACKORA_ADMIN_PASSWORD", "Admin12345!"))
    args = parser.parse_args()

    print(f"Trackora seeder -> {args.base_url}")

    # 1. Login -------------------------------------------------------------
    api = Api(args.base_url)
    status, data = api.post("/api/auth/login/", {"email": args.email, "password": args.password})
    if status != 200:
        raise SystemExit(f"Login failed ({status}): {data}\nCheck the email/password or that the server is running.")
    api.token = data["access"]
    print(f"  logged in as {data['user']['email']} ({data['user']['role']})\n")

    # 2. Categories (you already created these — they'll be reused) ---------
    categories = ensure(
        api, "/api/categories/", CATEGORIES,
        key_field="name", key_of_item=lambda c: c[0],
        build_payload=lambda c: {"name": c[0], "description": c[1]},
        label="Categories",
    )

    # 3. Suppliers ---------------------------------------------------------
    suppliers = ensure(
        api, "/api/suppliers/", SUPPLIERS,
        key_field="name", key_of_item=lambda s: s["name"],
        build_payload=lambda s: s,
        label="Suppliers",
    )

    # 4. Products ----------------------------------------------------------
    def product_payload(p):
        return {
            "name": p["name"], "sku": p["sku"],
            "category": categories[p["category"]]["id"],
            "supplier": suppliers[p["supplier"]]["id"],
            "unit": p["unit"],
            "cost_price": p["cost_price"], "selling_price": p["selling_price"],
            "reorder_level": p["reorder_level"],
        }

    ensure(
        api, "/api/products/", PRODUCTS,
        key_field="sku", key_of_item=lambda p: p["sku"],
        build_payload=product_payload,
        label="Products",
    )

    # Re-fetch products to get current ids + quantities
    products_by_sku = {p["sku"]: p for p in api.fetch_all("/api/products/")}

    # 5. Stock In — only for products that still have quantity 0 ------------
    by_supplier = {}
    for p in PRODUCTS:
        live = products_by_sku[p["sku"]]
        if live["quantity"] == 0:
            by_supplier.setdefault(p["supplier"], []).append(
                {"product": live["id"], "quantity": p["initial_qty"], "unit_cost": p["cost_price"]}
            )

    if by_supplier:
        receipts = 0
        for supplier_name, items in by_supplier.items():
            payload = {
                "supplier": suppliers[supplier_name]["id"],
                "note": f"Initial stock - {supplier_name}",
                "items": items,
            }
            status, data = api.post("/api/stock-in/", payload)
            if status not in (200, 201):
                raise SystemExit(f"  ! stock-in for {supplier_name} failed: {status} {data}")
            receipts += 1
        print(f"  Stock In: {receipts} receipt(s) created (set quantities for {sum(len(v) for v in by_supplier.values())} products)")
    else:
        print("  Stock In: skipped (all products already have stock)")

    # 6. Customers ---------------------------------------------------------
    customers = ensure(
        api, "/api/customers/", CUSTOMERS,
        key_field="name", key_of_item=lambda c: c["name"],
        build_payload=lambda c: c,
        label="Customers",
    )

    # 7. Orders + Stock-out — only on a fresh seed (no existing orders) -----
    existing_orders = api.fetch_all("/api/orders/")
    products_by_sku = {p["sku"]: p for p in api.fetch_all("/api/products/")}  # refresh after stock-in

    if existing_orders:
        print(f"  Orders: skipped ({len(existing_orders)} order(s) already exist)")
    else:
        made = 0
        for o in ORDERS:
            payload = {
                "customer": customers[o["customer"]]["id"] if o["customer"] else None,
                "payment_method": o["payment_method"],
                "discount": o["discount"],
                "line_items": [
                    {"product": products_by_sku[sku]["id"], "quantity": qty}
                    for sku, qty in o["items"]
                ],
            }
            status, data = api.post("/api/orders/", payload)
            if status in (200, 201):
                made += 1
            else:
                print(f"  ! order skipped ({status}): {data}")
        print(f"  Orders: {made} created")

        # Sample stock-out
        out = 0
        for so in STOCK_OUTS:
            payload = {
                "reason": so["reason"], "note": so["note"],
                "items": [
                    {"product": products_by_sku[sku]["id"], "quantity": qty}
                    for sku, qty in so["items"]
                ],
            }
            status, data = api.post("/api/stock-out/", payload)
            if status in (200, 201):
                out += 1
            else:
                print(f"  ! stock-out skipped ({status}): {data}")
        print(f"  Stock Out: {out} created")

    # 8. Summary -----------------------------------------------------------
    status, dash = api.get("/api/reports/dashboard/")
    if status == 200:
        print("\nDashboard now reports:")
        for key in ("total_products", "total_suppliers", "total_customers",
                    "low_stock_items", "total_orders", "today_sales", "monthly_sales",
                    "inventory_cost_value"):
            print(f"  {key:22s}: {dash.get(key)}")

    print("\nDone.")


if __name__ == "__main__":
    main()
