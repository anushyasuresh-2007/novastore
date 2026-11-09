# Novastore – Online Shopping Store

A complete, modern, production-deployed full-stack Online Shopping Store application built with **React 19 + Vite 6** on the frontend, **Python Flask 3.1 + Flask-SQLAlchemy** on the backend, **SQLite** for local development, and **Neon Cloud PostgreSQL** for production.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Production Deployments](#production-deployments)
3. [Key Features](#key-features)
4. [Technology Stack](#technology-stack)
5. [Architecture & Project Structure](#architecture--project-structure)
6. [Prerequisites](#prerequisites)
7. [Installation & Setup](#installation--setup)
8. [Database Setup & Seeding](#database-setup--seeding)
9. [Running the Application](#running-the-application)
10. [Automated Testing](#automated-testing)
11. [REST API Documentation](#rest-api-documentation)
12. [Security & Reliability](#security--reliability)
13. [Architecture & Documentation Index](#architecture--documentation-index)
14. [Screenshots Checklist](#screenshots-checklist)
15. [Assumptions & Limitations](#assumptions--limitations)
16. [Future Enhancements](#future-enhancements)
17. [Contributors](#contributors)

---

## Project Overview

**Novastore** is an end-to-end e-commerce web platform engineered with clean code clarity and senior-level architectural rigor. The application implements zero-trust pricing validation, atomic database transactions with rollback, inventory tracking, a centralized shopping cart with `localStorage` persistence, an Indian-context validated checkout flow, and an authenticated administrator portal.

The storefront catalogue displays 30 products across 6 categories (Electronics, Audio, Accessories, Home & Office, Wearables, and Photography), priced in Indian Rupees (`INR`, `₹`), while seamlessly preserving historical pre-migration orders.

---

## Production Deployments

| Component | Platform | Live URL | Deployment Notes |
| :--- | :--- | :--- | :--- |
| **Storefront & Admin UI** | Vercel | [https://novastore-tau.vercel.app](https://novastore-tau.vercel.app) | React 19 SPA with `/api/*` reverse-proxy rewrite to backend. |
| **REST API Backend** | Render | [https://novastore-api-2w65.onrender.com](https://novastore-api-2w65.onrender.com) | Python 3.13 / Gunicorn Linux Web Service. |
| **Production Database** | Neon | Cloud PostgreSQL | Managed serverless PostgreSQL with strict SSL enforcement. |

---

## Key Features

### A. Product Catalogue & Discovery
- **Dynamic Catalogue**: Displays products with high-resolution imagery, titles, descriptions, categories, INR prices (`₹`), and stock badges (`In Stock`, `Only X Left`, `Out of Stock`).
- **Real-Time Search**: Substring search matching product titles and category descriptions.
- **Category Filter Chips**: Dynamic category aggregation with live item counts fetched from the backend (`All`, `Accessories`, `Audio`, `Electronics`, `Home & Office`, `Photography`, `Wearables`).
- **Price Range Filtering**: Numerical minimum and maximum price filtering with strict boundary validation (`min_price <= max_price`).
- **Sorting Options**: Sort by price (low to high / high to low), product name (A–Z / Z–A), and featured/newest.
- **Product Details Modal**: Full specification modal showing item specifications, category tag, live stock status, and quantity stepper.

### B. Shopping Cart & Inventory Management
- **Centralized Cart State**: React Context (`CartContext`) managing items, quantities, and pricing calculations.
- **`localStorage` Persistence**: Cart contents automatically persist across page reloads and browser sessions (`novastore_cart_items`).
- **Strict Stock Boundaries**: Prevents adding out-of-stock items and prevents cart quantities from exceeding live warehouse stock.
- **Quantity Steppers**: Increment (`+`) and decrement (`–`) controls ensuring positive integer quantities.
- **Real-Time Financial Calculations**: Computes line totals, order subtotal, dynamic delivery fee (**Free for orders $\ge ₹999.00$; otherwise flat ₹99.00**), and estimated total amount.
- **Cart Management**: Individual item removal, "Clear Cart" action, and an empty-cart state with an "Explore Catalog" CTA.

### C. Checkout & Validation
- **Responsive Checkout Form**: Collects customer full name, email address, mobile phone number, delivery address, city, state, and postal code.
- **Indian-Context Validation**:
  - Full Name: Required, 2–120 characters.
  - Email: Standard RFC-compliant format regex.
  - Phone Number: 10-digit Indian mobile number (`^(?:\+91)?[6-9]\d{9}$`).
  - Postal Code: 6-digit Indian PIN code (`^\d{6}$`).
- **Inline Field Feedback**: Clear, instant error messages beneath invalid inputs.
- **Simulated Payment Notice**: Safe, simulated checkout notice reassuring users that no real credit card or debit card is charged.

### D. Order Processing & Transaction Safety
- **Zero-Trust Pricing Architecture**: The backend never trusts prices, subtotals, or delivery fees submitted by the client. Canonical prices and stock levels are always fetched directly from the database.
- **Atomic Database Transactions**: Orders and order items are inserted, and stock is decremented within an atomic transaction. Any exception triggers an immediate `db.session.rollback()`.
- **Database Stock Check Constraint**: PostgreSQL check constraint `check_product_stock_non_negative` guarantees inventory never drops below zero.
- **Unique Order Reference**: Collision-tested order references formatted as `ORD-YYYYMMDD-XXXXXXXX`.
- **Purchase Snapshots**: Product names and unit prices are saved as immutable purchase-time snapshots in `order_items`.
- **Dual-Currency Preservation**: Historical pre-migration orders retain their original USD currency (`$`), while all modern catalogue orders transact in INR (`₹`).
- **Cart Protection on Failure**: The shopping cart is cleared **only** after the backend returns HTTP 201 Created. If validation or order placement fails, cart items are preserved.

### E. Order Confirmation & Receipts
- **Confirmation Screen**: Displays confirmation checkmark, unique order reference, customer delivery information, order status (`CONFIRMED`), timestamp, itemized product table, and pricing breakdown.
- **Interactive Tools**: Single-click "Copy Code" reference button, "Print Receipt" (`window.print()`), and "Continue Shopping" button.

### F. Secure Admin Dashboard & Inventory Operations
- **Server-Side Authentication**: Secure login using Werkzeug cryptographic password hashing (`scrypt/pbkdf2`) and signed session cookies (`itsdangerous`).
- **HttpOnly Session Cookies**: Session tokens are stored in `admin_session` cookies configured with `HttpOnly=True`, `SameSite=Strict`, and `Secure=True` in production.
- **Synchronizer CSRF Protection**: State-changing operations require a matching `X-CSRF-Token` header.
- **Access Control & Protected APIs**: Administrative endpoints are guarded with the `@admin_required` decorator.
- **Executive Overview**: High-level KPI metric cards displaying total products, active catalogue items, total customer orders, total warehouse inventory, and gross sales.
- **Product Inventory Management**: Full 30-item table with status badges (`Active` / `Inactive`), inline stock adjusters (`+` / `–`), and safe product deactivation preserving historical customer receipts.
- **Order Management**: Order search, lifecycle status filtering (`PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`), and line-item snapshot modal.

---

## Technology Stack

| Layer | Technologies & Versions | Purpose / Role |
| :--- | :--- | :--- |
| **Frontend** | React 19, Vite 6, Vanilla CSS Tokens | Fast single-page application storefront and admin dashboard. |
| **Backend** | Python 3.13, Flask 3.1, Gunicorn 23.0 | Lightweight REST API server and WSGI runner. |
| **Database ORM** | Flask-SQLAlchemy 3.1 (wrapping SQLAlchemy 2.0.x) | Relational ORM, schema modeling, and transaction management. |
| **Development Database** | SQLite 3 (with `PRAGMA foreign_keys=ON`) | Lightweight, zero-config local relational database (`backend/instance/store.db`). |
| **Production Database** | Neon Managed PostgreSQL 16+ (`psycopg2-binary 2.9+`) | High-availability cloud PostgreSQL with strict SSL enforcement (`sslmode=require`). |
| **Security & Utilities** | Werkzeug 3.1 (`ProxyFix`), `itsdangerous 2.2`, `python-dotenv 1.0` | Password hashing, trusted proxy handling, cryptographic tokens, and environment loading. |
| **Hosting & Edge** | Vercel (Frontend), Render (Backend) | Edge CDN static hosting, rewrite proxying, and containerized WSGI execution. |
| **Testing** | Pytest 8.4 (Backend), Node.js Test Runner (Frontend) | Full test suites covering APIs, edge cases, security, and cart logic. |

---

## Architecture & Project Structure

```text
D:\E-Commerce\
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── __init__.py         # Model package exports
│   │   │   ├── db.py               # SQLAlchemy instance & SQLite PRAGMA listener
│   │   │   ├── product.py          # Product model & non-negative check constraint
│   │   │   ├── order.py            # Order model & customer details
│   │   │   ├── order_item.py       # OrderItem immutable purchase-time snapshots
│   │   │   └── admin.py            # Admin model & password hash helpers
│   │   ├── routes/
│   │   │   ├── __init__.py         # Blueprint exports
│   │   │   ├── product_routes.py   # GET /api/products, /api/categories, /api/products/<id>
│   │   │   ├── order_routes.py     # POST /api/orders, GET /api/orders/<reference>
│   │   │   └── admin_routes.py     # /api/admin/login, /me, /stats, /products, /orders
│   │   ├── services/
│   │   │   ├── __init__.py         # Service layer exports
│   │   │   ├── product_service.py  # Product query filtering, category aggregation
│   │   │   ├── order_service.py    # Zero-trust calculation, stock check, atomic rollback
│   │   │   ├── auth_service.py     # Admin authentication, session tokens, CSRF tokens
│   │   │   ├── admin_service.py    # Dashboard KPI metrics, order status state machine
│   │   │   └── rate_limiter.py     # In-memory sliding-window IP rate limiter
│   │   ├── __init__.py             # Flask create_app factory, CORS, ProxyFix setup
│   │   ├── config.py               # Development, Testing, and Production configs
│   │   └── database.py             # Schema creation and sample seed data
│   ├── instance/
│   │   └── store.db                # Local SQLite database (untracked in Git)
│   ├── scripts/
│   │   └── migrate_sqlite_to_postgres.py # Safe SQLite to Neon PostgreSQL migration engine
│   ├── tests/
│   │   ├── conftest.py             # Pytest fixtures (:memory: SQLite database)
│   │   ├── test_admin_api.py       # Admin authentication, stats, and order status tests
│   │   ├── test_app.py             # Application factory & configuration tests
│   │   ├── test_database.py        # Seeding idempotency, foreign keys, and rollbacks
│   │   ├── test_e2e_journey.py     # End-to-end shopping journey test
│   │   ├── test_edge_cases.py      # Concurrency, injection, and phone/PIN edge cases
│   │   ├── test_migration_script.py# Database migration dry-run and sequence tests
│   │   ├── test_models.py          # Model constraints and cascade deletes
│   │   ├── test_orders_api.py      # Checkout creation and zero-trust pricing tests
│   │   ├── test_products_api.py    # Catalogue, search, and category filter tests
│   │   └── test_security_hardening.py # Secret key, CORS, and rate limiting tests
│   ├── create_admin.py             # Standalone CLI for admin account provisioning
│   ├── create_backup.py            # SQLite timestamped backup generator
│   ├── migrate_to_inr.py           # Standalone INR currency migration script
│   ├── pytest.ini                  # Backend pytest configuration
│   ├── requirements.txt            # Python dependencies (Flask, Gunicorn, Psycopg2)
│   ├── rotate_admin_password.py    # Secure admin credential rotation utility
│   ├── run.py                      # Local development runner
│   └── seed.py                     # Standalone database seed script
│
├── frontend/
│   ├── dist/                       # Vite compiled production output
│   ├── src/
│   │   ├── components/
│   │   │   ├── admin/
│   │   │   │   └── AdminNavbar.jsx # Navigation header for administrator portal
│   │   │   ├── EmptyState.jsx      # Zero-results state with filter reset action
│   │   │   ├── FilterBar.jsx       # Search input, category chips, price filter, sorting
│   │   │   ├── Footer.jsx          # Semantic footer
│   │   │   ├── Hero.jsx            # Value proposition header banner
│   │   │   ├── LoadingState.jsx    # Animated loading spinner
│   │   │   ├── Navbar.jsx          # Storefront navigation bar with live cart count
│   │   │   ├── NotificationToast.jsx # Slide-in notification alerts
│   │   │   ├── ProductCard.jsx     # Product card with stock badges and Add to Cart
│   │   │   └── ProductDetailsModal.jsx # Full specifications modal with quantity selector
│   │   ├── context/
│   │   │   ├── AdminAuthContext.jsx# React Context for admin session and CSRF tokens
│   │   │   └── CartContext.jsx     # React Context for shopping cart & localStorage
│   │   ├── pages/
│   │   │   ├── admin/
│   │   │   │   ├── AdminDashboardPage.jsx # Executive overview KPIs and recent orders
│   │   │   │   ├── AdminLoginPage.jsx     # Administrator credentials sign-in
│   │   │   │   ├── AdminOrdersPage.jsx    # Order fulfillment and status updater
│   │   │   │   ├── AdminPortal.jsx        # Admin route container
│   │   │   │   └── AdminProductsPage.jsx  # Inventory CRUD and stock adjustments
│   │   │   ├── CartPage.jsx        # Shopping cart view with order summary
│   │   │   ├── CatalogPage.jsx     # Main storefront catalogue view
│   │   │   ├── CheckoutPage.jsx    # Checkout form with Indian validation
│   │   │   └── OrderConfirmationPage.jsx # Order receipt with reference code
│   │   ├── services/
│   │   │   ├── adminApi.js         # Authorized fetch client with HttpOnly cookies & CSRF
│   │   │   └── api.js              # Storefront API client
│   │   ├── utils/
│   │   │   └── currency.js         # Dual-currency formatting utility (INR & USD)
│   │   ├── App.jsx                 # View router and root layout
│   │   ├── main.jsx                # React root mount
│   │   └── style.css               # Vanilla CSS design tokens
│   ├── tests/
│   │   ├── admin_frontend_logic.test.mjs  # Admin UI logic and transition tests
│   │   ├── api_client.test.mjs     # API client query string tests
│   │   ├── cart_logic.test.mjs     # Cart state, stock capping, and currency tests
│   │   └── checkout_validation.test.mjs # Form validation and cart clearing tests
│   ├── .env.example                # Frontend environment configuration template
│   ├── index.html                  # HTML5 entry with Google Inter font
│   ├── package.json                # Frontend dependencies and scripts
│   ├── vercel.json                 # Vercel reverse proxy rewrite configuration
│   └── vite.config.js              # Vite server & /api proxy to localhost:5000
│
├── .gitignore                      # Git exclusion rules (.venv, node_modules, *.db)
├── .env.example                    # High-level environment variable template
├── ARCHITECTURE.md                 # System architecture & Mermaid flowcharts
├── DATABASE_MIGRATION.md           # SQLite to PostgreSQL migration guide
├── DEPLOYMENT.md                   # Vercel, Render, and Neon deployment guide
├── SECURITY.md                     # Security controls, cookies, CSRF, and limitations
├── pytest.ini                      # Root pytest configuration
└── README.md                       # Complete project documentation
```

---

## Prerequisites

Ensure the following tools are installed on your workstation:

- **Python**: Version 3.13+ (or 3.11+)
- **Node.js**: Version 20+ (v24.14.0 recommended)
- **npm**: Version 10+
- **Git**: Version 2.40+
- **Shell**: Windows PowerShell (or Bash on macOS/Linux)

---

## Installation & Setup

### 1. Clone the Repository
```powershell
git clone https://github.com/anushyasuresh-2007/novastore.git
cd novastore
```

### 2. Backend Setup
Create and activate the virtual environment, then install Python dependencies:

```powershell
# Navigate to the backend directory
cd backend

# Create virtual environment (if not already present)
python -m venv .venv

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1   # On Windows PowerShell
# source .venv/bin/activate    # On Linux/macOS

# Install required dependencies
python -m pip install -r requirements.txt
```

### 3. Frontend Setup
Install Node dependencies:

```powershell
# Navigate to the frontend directory
cd ..\frontend

# Install node modules
npm install
```

---

## Database Setup & Seeding

The local SQLite database file is stored in `backend/instance/store.db`.

To initialize the database schema and populate it with 30 sample products across 6 categories (Electronics, Audio, Accessories, Home & Office, Wearables, and Photography):

```powershell
# From backend directory with .venv activated
python seed.py
```

*Output:*
```text
Initializing database...
Creating database tables...
Seeding sample products...
Successfully seeded 18 new products into the database.
Done! 30 products available in database.
```

The database seeding logic is **idempotent and safe**: running `python seed.py` repeatedly will never overwrite existing product prices, never reset inventory for products with orders, and never create duplicate records.

### Administrator Provisioning & Password Rotation

Administrator accounts cannot be registered through public web endpoints. Use one of the secure utilities below:

#### Creating an Administrator
```powershell
cd backend
.\.venv\Scripts\Activate.ps1

# Interactive masked prompt (Recommended)
python create_admin.py
```

#### Rotating Administrator Password
```powershell
# Interactive masked prompt
python rotate_admin_password.py --username admin
```

*Security Assurance:* Rotating the administrator password updates the `updated_at` timestamp on the admin record, which immediately revokes all active session tokens across all browsers.

---

## Running the Application

Run the backend and frontend in two separate terminal windows:

### Terminal 1: Backend Server (Flask API)
```powershell
cd D:\E-Commerce\backend
.\.venv\Scripts\Activate.ps1
python run.py
```
- The backend REST API starts on: **`http://127.0.0.1:5000`**
- Health check route: **`http://127.0.0.1:5000/api/health`**

### Terminal 2: Frontend Server (Vite React)
```powershell
cd D:\E-Commerce\frontend
npm run dev
```
- The frontend is accessible at: **`http://localhost:5173`**
- API requests made to `/api/*` are automatically proxied to `http://127.0.0.1:5000`.

---

## Automated Testing

### 1. Backend Pytest Suite
The backend tests run against an isolated in-memory SQLite database (`sqlite:///:memory:`) and never modify development or production databases.

```powershell
# Run from repository root
cd D:\E-Commerce
& .\backend\.venv\Scripts\python.exe -m pytest backend
```

> [!NOTE]
> *Audit Result (November 9, 2026 Audit):* **157 passed in ~7.4s** across 10 test modules (including 30 tests in `test_migration_script.py` which validate the database migration engine and 54 tests in `test_security_hardening.py`). Test counts reflect the verified local test suite and will be 120 on a fresh clone of baseline commit `e6423cd` prior to staging migration scripts. Tests never touch development or production databases.

#### Test Suite Structure:
- **`test_admin_api.py`** (21 tests): Admin login, cookie auth, dashboard stats, product CRUD, soft-deletions, order filtering, and status state transitions.
- **`test_app.py`** (1 test): Application factory and development configurations.
- **`test_database.py`** (7 tests): Seeding idempotency, foreign keys, transaction rollbacks, and SQLite PRAGMA compatibility.
- **`test_e2e_journey.py`** (1 test): Complete 11-step customer shopping journey from browsing to stock deduction.
- **`test_edge_cases.py`** (8 tests): Reference collision resistance, duplicate product ID aggregation, sequential stock depletion, Indian phone/PIN validation, and SQL injection safety.
- **`test_migration_script.py`** (30 tests): SQLite-to-PostgreSQL migration dry-run isolation, transaction atomicity, sequence synchronization, and divergence detection.
- **`test_models.py`** (4 tests): Non-negative price/stock check constraints, cascade deletions, and purchase snapshot retention.
- **`test_orders_api.py`** (12 tests): Checkout creation, customer validation, quantity checks, zero-trust price recalculation, and delivery fee rules.
- **`test_products_api.py`** (19 tests): Catalogue retrieval, 30 products assertion, 6 categories including Photography, category filters, price bounds, and sort orders.
- **`test_security_hardening.py`** (54 tests): Production `SECRET_KEY` enforcement, wildcard CORS rejection, admin password policy, rate limiting (canonical env loading, legacy fallback, precedence, defaults, time-mocked expiry, reset), and trusted proxy handling.

### 2. Frontend Automated Tests
Runs natively using the Node.js test runner:

```powershell
cd D:\E-Commerce\frontend
npm test
```

> [!NOTE]
> *Audit Result (November 9, 2026 Audit):* **29 passed in ~280ms** across 4 test suites (`admin_frontend_logic`, `api_client`, `cart_logic`, `checkout_validation`).

### 3. Frontend Production Build
To verify that the application compiles cleanly for production:

```powershell
cd D:\E-Commerce\frontend
npm run build
```

---

## REST API Documentation

### 1. `GET /api/health`
Verify server and database operational health.

**Sample Response (HTTP 200 OK):**
```json
{
  "status": "healthy",
  "environment": "production",
  "database": "connected"
}
```

---

### 2. `GET /api/products`
Retrieve catalogue products with optional search, category, price bounds, and sorting.

**Query Parameters:**
- `search` (string): Search term matching product names or descriptions.
- `category` (string): Filter by category name (e.g. `Electronics`, `Audio`, `Photography`).
- `min_price` (float): Minimum price in INR.
- `max_price` (float): Maximum price in INR.
- `sort` (string): `price_asc`, `price_desc`, `name_asc`, `name_desc`, or `newest`.

**Sample Response (HTTP 200 OK):**
```json
{
  "count": 6,
  "filters": {
    "category": "Electronics",
    "max_price": null,
    "min_price": null,
    "search": null,
    "sort": null
  },
  "products": [
    {
      "id": 1,
      "name": "Ultra-Slim Wireless Mechanical Keyboard",
      "category": "Electronics",
      "currency": "INR",
      "price": 6999.0,
      "stock_quantity": 22,
      "description": "Low-profile mechanical switches with RGB backlighting, Bluetooth 5.3, and multi-device pairing.",
      "image_path": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
      "is_active": true,
      "created_at": "2026-11-01T15:09:34.481199",
      "updated_at": "2026-11-06T17:07:35.448890"
    }
  ]
}
```

---

### 3. `GET /api/products/<int:id>`
Retrieve complete details of a specific product.

**Sample Response (HTTP 200 OK):**
```json
{
  "id": 1,
  "name": "Ultra-Slim Wireless Mechanical Keyboard",
  "category": "Electronics",
  "currency": "INR",
  "price": 6999.0,
  "stock_quantity": 22,
  "description": "Low-profile mechanical switches with RGB backlighting...",
  "image_path": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80",
  "is_active": true,
  "created_at": "2026-11-01T15:09:34.481199",
  "updated_at": "2026-11-06T17:07:35.448890"
}
```

---

### 4. `GET /api/categories`
Retrieve all available categories and live product counts.

**Sample Response (HTTP 200 OK):**
```json
{
  "categories": [
    { "name": "Accessories", "count": 4 },
    { "name": "Audio", "count": 6 },
    { "name": "Electronics", "count": 6 },
    { "name": "Home & Office", "count": 6 },
    { "name": "Photography", "count": 4 },
    { "name": "Wearables", "count": 4 }
  ]
}
```

---

### 5. `POST /api/orders`
Place a new order with simulated checkout.

**Request Body:**
```json
{
  "customer_name": "NovaStore QA Tester",
  "customer_email": "qa-test@novastore.internal",
  "customer_phone": "9876543210",
  "delivery_address": "Test Suite 101, Ground Floor",
  "city": "Bengaluru",
  "state": "Karnataka",
  "postal_code": "560001",
  "items": [
    { "product_id": 1, "quantity": 1 }
  ]
}
```

**Sample Response (HTTP 201 Created):**
```json
{
  "message": "Order placed successfully",
  "order": {
    "id": 5,
    "order_reference": "ORD-YYYYMMDD-XXXXXXXX",
    "customer_name": "NovaStore QA Tester",
    "customer_email": "qa-test@novastore.internal",
    "customer_phone": "9876543210",
    "delivery_address": "Test Suite 101, Ground Floor, Karnataka",
    "city": "Bengaluru",
    "postal_code": "560001",
    "currency": "INR",
    "subtotal": 6999.0,
    "delivery_fee": 0.0,
    "total_amount": 6999.0,
    "status": "CONFIRMED",
    "created_at": "2026-11-06T17:07:35.433546",
    "items": [
      {
        "id": 5,
        "order_id": 5,
        "product_id": 1,
        "product_name": "Ultra-Slim Wireless Mechanical Keyboard",
        "currency": "INR",
        "unit_price": 6999.0,
        "quantity": 1,
        "line_total": 6999.0
      }
    ]
  }
}
```

---

### 6. `GET /api/orders/<string:reference>`
Fetch an order's confirmation details by its reference.

**Sample Response (HTTP 200 OK):**
```json
{
  "order": {
    "order_reference": "ORD-YYYYMMDD-XXXXXXXX",
    "status": "CONFIRMED",
    "customer_name": "NovaStore QA Tester",
    "customer_email": "qa-test@novastore.internal",
    "customer_phone": "9876543210",
    "delivery_address": "Test Suite 101, Ground Floor, Karnataka",
    "city": "Bengaluru",
    "postal_code": "560001",
    "currency": "INR",
    "subtotal": 6999.0,
    "delivery_fee": 0.0,
    "total_amount": 6999.0,
    "created_at": "2026-11-06T17:07:35.433546",
    "items": []
  }
}
```

---

### 7. Administrator API Endpoints (Protected: Session Cookie & CSRF)

All endpoints below require an authenticated `admin_session` cookie. State-changing requests (`POST`, `PUT`, `PATCH`, `DELETE`) also require the `X-CSRF-Token` header.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/admin/login` | Authenticate admin credentials and issue secure `HttpOnly` session cookie. |
| `POST` | `/api/admin/logout` | Terminate administrator session and clear cookies. |
| `GET` | `/api/admin/me` | Verify session validity and fetch authenticated profile. |
| `GET` | `/api/admin/stats` | Retrieve KPI metrics (sales, orders, inventory, recent orders). |
| `GET` | `/api/admin/products` | Retrieve all catalogue products with status and stock filters. |
| `POST` | `/api/admin/products` | Create a new product in the inventory. |
| `GET` | `/api/admin/products/<id>` | Fetch a specific product's full record. |
| `PUT` | `/api/admin/products/<id>` | Update product details, price, inventory, or visibility. |
| `DELETE` | `/api/admin/products/<id>` | Safely soft-archive or permanently delete a product. |
| `GET` | `/api/admin/orders` | Retrieve customer orders with status filter and search. |
| `GET` | `/api/admin/orders/<id_or_ref>` | Fetch full order details including line item snapshots. |
| `PATCH` | `/api/admin/orders/<id_or_ref>/status` | Update fulfillment status (`PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`). |

---

## Security & Reliability

- **Zero-Trust Pricing**: All totals, subtotals, and delivery charges are calculated exclusively on the backend from database prices. Frontend prices are disregarded.
- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy ORM; tested against malicious injection payloads.
- **Concurrency & Stock Integrity**: Orders are validated against live warehouse inventory; database check constraints and atomic transactions guarantee rollback on stock conflicts.
- **Session Protection**: Administrator sessions are protected by `HttpOnly`, `SameSite=Strict`, and `Secure` cookies with synchronizer CSRF tokens.
- **Rate Limiting**: In-memory sliding-window rate limiting on login (5/min) and order placement (10/min) per IP address.
- **Information Disclosure Protection**: Production error handlers return clean JSON error messages and suppress stack traces.

---

## Architecture & Documentation Index

For in-depth guides covering specific domains of NovaStore, refer to:

- **[ARCHITECTURE.md](./ARCHITECTURE.md)**: High-level architectural diagrams, data flows, and component responsibilities.
- **[DEPLOYMENT.md](./DEPLOYMENT.md)**: Production deployment instructions for Vercel, Render, and Neon, including environment variables and smoke tests.
- **[DATABASE_MIGRATION.md](./DATABASE_MIGRATION.md)**: Database migration engine details, sequence synchronization, dry-run modes, and recovery procedures.
- **[SECURITY.md](./SECURITY.md)**: Security policy, cookie parameters, CSRF validation, and documented architectural boundaries.

---

## Screenshots Checklist

When preparing project submission media, capture the following application views:

- [ ] **1. Storefront & Product Catalogue**: Landing page showing navigation bar, live cart count badge, hero banner, category chips, and product grid with INR prices.
- [ ] **2. Search & Filtering in Action**: Products filtered by category (e.g. `Electronics`, `Audio`, `Photography`) and sorted by price.
- [ ] **3. Product Details Modal**: Open modal showcasing product specifications, category tag, live stock status, and quantity stepper.
- [ ] **4. Shopping Cart Page**: Cart view displaying items with line totals, quantity controls (`+` / `–`), subtotal, dynamic free delivery hint, and order summary.
- [ ] **5. Empty Cart State**: View displayed when all items are cleared from the cart with the "Explore Catalog" CTA.
- [ ] **6. Checkout Page**: Shipping form with customer inputs, Indian phone and PIN validation indicators, and simulated payment notice.
- [ ] **7. Order Confirmation Page**: Complete receipt screen showing the green success badge, unique order reference (`ORD-YYYYMMDD-XXXXXXXX`), and itemized purchase snapshot table.
- [ ] **8. Admin Login Portal**: Secure authentication screen with username/email and password fields.
- [ ] **9. Admin Executive Overview**: Dashboard KPI metrics cards, status breakdown pills, and recent customer orders table.
- [ ] **10. Admin Product Inventory**: Full 30-item table with status badges, inline stock adjusters, and Add/Edit modal.
- [ ] **11. Admin Order Fulfillment**: Orders table with status filters and detailed Order Details Modal with purchase snapshots.
- [ ] **12. Terminal & Passing Tests**: Terminal showing all 157 backend tests passing and 29 frontend tests passing.

---

## Assumptions & Limitations

- **Simulated Checkout**: Real credit card and payment gateway integration (e.g. Stripe, Razorpay) is omitted by design; checkout simulates direct confirmed order placement.
- **Local Storage Cart**: Shopping cart state is stored in browser `localStorage`. Cart contents are specific to the user's browser until order checkout.
- **Rate Limiting Scope**: Built-in sliding-window rate limiting is in-memory per worker process; a multi-worker production cluster would utilize Redis for globally synchronized rate limit buckets.

---

## Future Enhancements

- [ ] Customer account authentication (JWT or customer session cookies) for profile management and order history tracking.
- [ ] Payment gateway integration with Razorpay or Stripe webhooks.
- [ ] Distributed rate limiting using Redis.
- [ ] Automated email confirmations sent via SendGrid or AWS SES upon order creation.
- [ ] Algorithmic typo tolerance and fuzzy product search.

---

## Contributors

- **Author**: Anushya Suresh ([@anushyasuresh-2007](https://github.com/anushyasuresh-2007))
- **Project**: NovaStore Full-Stack Online Shopping Store
- **License**: MIT License
