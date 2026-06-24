# Trackora — Hardware Store Management Backend

Trackora is a REST API backend for managing a hardware store that deals in products such as
cement, iron sheets, paint, pipes, tiles, nails, and electrical cables. It provides everything a
shop needs to run day-to-day operations: a role-based user system, a product catalogue with
suppliers and categories, stock-in / stock-out tracking with automatic quantity adjustment, a
point-of-sale ordering flow that deducts stock and records profit, and a reporting layer that
powers dashboards (low stock, daily/monthly sales, profit, best sellers). It is built to be
consumed by a React frontend and ships with JWT authentication, filtering, pagination, a
customised Django admin, and a full Docker setup.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Folder Structure](#folder-structure)
- [Environment Variables](#environment-variables)
- [Database Setup](#database-setup)
- [Installation & Running (Local)](#installation--running-local)
- [Running with Docker](#running-with-docker)
- [Default Accounts](#default-accounts)
- [User Roles & Permissions](#user-roles--permissions)
- [API Endpoint Summary](#api-endpoint-summary)
- [Authentication Flow](#authentication-flow)
- [Business Logic Notes](#business-logic-notes)
- [Admin Site](#admin-site)

---

## Tech Stack

| Layer            | Technology                                   |
|------------------|----------------------------------------------|
| Language         | Python 3.13                                  |
| Framework        | Django 6.0                                   |
| API              | Django REST Framework 3.17                   |
| Authentication   | JWT via `djangorestframework-simplejwt`      |
| Database         | PostgreSQL 16                                |
| Filtering        | `django-filter`                              |
| CORS             | `django-cors-headers`                        |
| Image handling   | `Pillow`                                     |
| Static files     | `WhiteNoise`                                 |
| WSGI server      | `Gunicorn`                                   |
| Containerisation | Docker + Docker Compose                      |

---

## Features

- **Accounts** — custom email-based user, JWT login/refresh, registration, profile, password change,
  and Admin-managed user accounts with three roles.
- **Inventory** — categories, suppliers, and products with SKU, cost/selling price, units, reorder
  levels, images, search, filtering, and pagination.
- **Stock** — stock-in and stock-out records (with line items) that atomically adjust product
  quantities, plus auto-generated reference numbers and low-stock detection.
- **Sales** — customers and orders. Creating an order snapshots prices, deducts stock, and records
  profit; cancelling an order restores stock.
- **Reports** — dashboard KPIs, low-stock, daily/monthly sales, profit, and best-selling products.
- **Admin** — a customised Django admin for back-office management.

---

## Prerequisites

Make sure you have the following installed:

- **Python 3.13+**
- **PostgreSQL 13+** (16 recommended)
- **pip** and **virtualenv** (bundled with modern Python)
- **Git**
- *(Optional, for containers)* **Docker Desktop** with Docker Compose

---

## Folder Structure

```
trackora_backend/
├── manage.py
├── requirements.txt
├── .env                       # environment variables (not committed)
├── .gitignore
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh              # container startup: wait-for-db, migrate, collectstatic, gunicorn
│
├── config/                    # project configuration
│   ├── settings.py            # env-driven settings (DRF, JWT, CORS, Postgres, media)
│   ├── urls.py                # root URL routing
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── accounts/              # custom User, roles, JWT auth, permissions
│   ├── inventory/             # Category, Supplier, Product (+ filters)
│   ├── stock/                 # StockIn / StockOut (+ items, quantity logic)
│   ├── sales/                 # Customer, Order, OrderItem (auto stock deduction)
│   └── reports/               # dashboard & analytics endpoints
│
└── media/                     # uploaded product images
    └── products/
```

Each app follows the standard Django layout (`models.py`, `serializers.py`, `views.py`, `urls.py`,
`admin.py`, and `migrations/`). The `accounts` app additionally has `managers.py` and
`permissions.py`; `inventory` has `filters.py`; `stock` has `utils.py` (reference generation).

---

## Environment Variables

Configuration is loaded from a `.env` file at the project root (via `python-dotenv`). A
template is provided as `.env.example` — copy it and fill in your own values:

```bash
cp .env.example .env
```

Generate a strong `SECRET_KEY`:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

- **`SECRET_KEY`** — Django cryptographic key. Use a unique, generated value per environment.
- **`DEBUG`** — `True` for development, `False` for production.
- **`ALLOWED_HOSTS`** — comma-separated hostnames allowed to serve the app.
- **`DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT`** — PostgreSQL connection details.
- **`CORS_ALLOWED_ORIGINS`** — comma-separated frontend origins permitted via CORS.

> **Security:** `.env` is git-ignored — only `.env.example` (with placeholder values) is committed.
> Never commit real secrets, and always set a strong `SECRET_KEY`, a non-default database password,
> and `DEBUG=False` in production.

---

## Database Setup

The project uses **PostgreSQL**. Create the database before running migrations.

**Option A — using `psql`:**

```sql
CREATE DATABASE trackora_db;
```

**Option B — using `createdb`:**

```bash
createdb -U postgres trackora_db
```

**Option C — without psql on PATH (via Python/psycopg2):**

```bash
python -c "import psycopg2; from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT as A; \
c=psycopg2.connect(dbname='postgres',user='postgres',password='postgres',host='localhost'); \
c.set_isolation_level(A); c.cursor().execute('CREATE DATABASE trackora_db')"
```

Make sure the credentials in `.env` match your PostgreSQL setup.

---

## Installation & Running (Local)

```bash
# 1. Clone and enter the project
git clone <your-repo-url> trackora_backend
cd trackora_backend

# 2. Create and activate a virtual environment
python -m venv venv
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# macOS / Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create your .env file (see Environment Variables above)

# 5. Create the PostgreSQL database (see Database Setup above)

# 6. Apply migrations
python manage.py migrate

# 7. Create an admin user
python manage.py createsuperuser

# 8. Run the development server
python manage.py runserver
```

The API will be available at **http://127.0.0.1:8000/**.

| URL                              | Purpose                |
|----------------------------------|------------------------|
| `http://127.0.0.1:8000/`         | Health check           |
| `http://127.0.0.1:8000/api/`     | API root               |
| `http://127.0.0.1:8000/admin/`   | Django admin           |

---

## Running with Docker

The repository includes a `Dockerfile` and `docker-compose.yml` that run the API together with a
PostgreSQL service. The startup script waits for the database, applies migrations, collects static
files, then launches Gunicorn.

```bash
# Build and start the full stack (API + Postgres) in the background
docker compose up -d --build

# Create an admin user inside the running container
docker compose exec web python manage.py createsuperuser

# Follow API logs
docker compose logs -f web

# Stop the stack (data is preserved in volumes)
docker compose down

# Stop and wipe the database volume (fresh start)
docker compose down -v
```

| Service | Host port | Container port | Notes                                            |
|---------|-----------|----------------|--------------------------------------------------|
| `web`   | `8000`    | `8000`         | The API (Gunicorn).                              |
| `db`    | `5433`    | `5432`         | PostgreSQL. Host port is **5433** to avoid clashing with a local Postgres on 5432. |

> The containerised database is **separate** from any local PostgreSQL instance; it lives in a
> Docker volume (`pgdata`).

Once running, the API is at **http://localhost:8000/**.

---

## Default Accounts

The project ships with **no pre-seeded accounts**. Create the first administrator yourself:

```bash
python manage.py createsuperuser
```

You'll be prompted for an email and password — choose a strong password. This account has the
**Admin** role and full access. Once it exists, additional **Manager** and **Staff** users can be
created by an Admin via `POST /api/auth/register/` or the `/api/auth/users/` endpoint.

---

## User Roles & Permissions

| Role        | Capabilities                                                        |
|-------------|---------------------------------------------------------------------|
| **Admin**   | Full access to everything, including user management.               |
| **Manager** | Manage products, categories, suppliers, stock, orders, and reports. |
| **Staff**   | Record stock in/out and create orders/customers.                    |

Permission summary by resource:

- **Products / Categories / Suppliers** — any authenticated user can read; only Manager/Admin can create or edit.
- **Stock In / Stock Out** — Staff, Manager, and Admin can record movements.
- **Customers / Orders** — Staff, Manager, and Admin; cancelling an order is Manager/Admin only.
- **Reports** — the dashboard is open to any authenticated user; other reports are Manager/Admin.
- **User management** — Admin only.

---

## API Endpoint Summary

Base URL: `http://localhost:8000`

### Authentication & Users — `/api/auth/`

| Method                  | Endpoint                    | Description                          |
|-------------------------|-----------------------------|--------------------------------------|
| POST                    | `/api/auth/register/`       | Register a user (Admin, or first user) |
| POST                    | `/api/auth/login/`          | Obtain access & refresh tokens       |
| POST                    | `/api/auth/refresh/`        | Refresh an access token              |
| GET / PATCH             | `/api/auth/profile/`        | View / update your own profile       |
| POST                    | `/api/auth/change-password/`| Change your password                 |
| GET / POST              | `/api/auth/users/`          | List / create users (Admin)          |
| GET / PUT / PATCH / DELETE | `/api/auth/users/<id>/`  | Manage a user (Admin)                |

### Inventory — `/api/`

| Method                     | Endpoint                  | Description                |
|----------------------------|---------------------------|----------------------------|
| GET / POST                 | `/api/categories/`        | List / create categories   |
| GET / PUT / PATCH / DELETE | `/api/categories/<id>/`   | Manage a category          |
| GET / POST                 | `/api/suppliers/`         | List / create suppliers    |
| GET / PUT / PATCH / DELETE | `/api/suppliers/<id>/`    | Manage a supplier          |
| GET / POST                 | `/api/products/`          | List / create products     |
| GET / PUT / PATCH / DELETE | `/api/products/<id>/`     | Manage a product           |

**Product filtering examples:**

```
/api/products/?search=cement
/api/products/?category=1&low_stock=true
/api/products/?min_price=1000&max_price=50000&ordering=-selling_price
/api/products/?page=2
```

### Stock — `/api/`

| Method      | Endpoint              | Description                                  |
|-------------|-----------------------|----------------------------------------------|
| GET / POST  | `/api/stock-in/`      | List / create stock-in (increases quantity)  |
| GET         | `/api/stock-in/<id>/` | Retrieve a stock-in record                   |
| GET / POST  | `/api/stock-out/`     | List / create stock-out (decreases quantity) |
| GET         | `/api/stock-out/<id>/`| Retrieve a stock-out record                  |

### Sales — `/api/`

| Method                     | Endpoint                  | Description                       |
|----------------------------|---------------------------|-----------------------------------|
| GET / POST / PUT / PATCH / DELETE | `/api/customers/` , `/api/customers/<id>/` | Manage customers |
| GET / POST                 | `/api/orders/`            | List / create orders (deducts stock) |
| GET                        | `/api/orders/<id>/`       | Retrieve an order                 |
| POST                       | `/api/orders/<id>/cancel/`| Cancel an order (restores stock)  |

### Reports — `/api/reports/`

| Method | Endpoint                       | Query params      | Description                     |
|--------|--------------------------------|-------------------|---------------------------------|
| GET    | `/api/reports/dashboard/`      | —                 | Dashboard KPIs                  |
| GET    | `/api/reports/low-stock/`      | —                 | Products at/below reorder level |
| GET    | `/api/reports/daily-sales/`    | `?days=30`        | Sales grouped by day            |
| GET    | `/api/reports/monthly-sales/`  | `?months=12`      | Sales grouped by month          |
| GET    | `/api/reports/profit/`         | `?days=30`        | Revenue, cost, profit, margin   |
| GET    | `/api/reports/best-selling/`   | `?limit=10`       | Top products by units sold      |

---

## Authentication Flow

1. **Log in** to obtain tokens:

   ```http
   POST /api/auth/login/
   Content-Type: application/json

   { "email": "you@example.com", "password": "your-password" }
   ```

   Response:

   ```json
   {
     "refresh": "<refresh_token>",
     "access": "<access_token>",
     "user": { "id": 1, "email": "you@example.com", "role": "admin", ... }
   }
   ```

2. **Send the access token** on every protected request:

   ```http
   Authorization: Bearer <access_token>
   ```

3. **Refresh** when the access token expires (default lifetime 12 hours):

   ```http
   POST /api/auth/refresh/
   { "refresh": "<refresh_token>" }
   ```

### Example: creating a product

```http
POST /api/products/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Hima 50kg Bag", "sku": "CEM-001",
  "category": 1, "supplier": 1,
  "unit": "bag", "cost_price": "28000", "selling_price": "32000",
  "reorder_level": 20
}
```

### Example: creating an order (auto-deducts stock)

```http
POST /api/orders/
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "payment_method": "cash",
  "line_items": [ { "product": 1, "quantity": 30 } ]
}
```

---

## Business Logic Notes

- **Product quantity is not editable directly** through the product API — it only changes via
  stock-in, stock-out, and orders. This keeps inventory counts trustworthy.
- **Stock movements are atomic.** Receiving stock increases quantity; selling or removing stock
  decreases it, with a guard that prevents selling/removing more than is available.
- **Orders snapshot prices.** Each order item stores the selling price and cost price at the time of
  sale, so historical orders and profit reports stay accurate even if prices change later.
- **Cancelling an order restores stock** and marks the order as cancelled (Manager/Admin only).
- **Reference numbers** for stock and orders are auto-generated, e.g. `SIN-20260624-0001`
  (stock in), `SOUT-...` (stock out), `ORD-...` (orders).

---

## Admin Site

A customised Django admin is available at `/admin/` for back-office management of users, products,
suppliers, categories, stock movements, customers, and orders. Log in with a superuser account.
Stock and order records are read-only in the admin so their quantity side-effects can't be bypassed
— record those through the API.

---

## License

Proprietary — © Trackora. All rights reserved. Unauthorized copying, distribution, or use of this
software is prohibited without prior written permission.
