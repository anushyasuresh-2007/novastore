# Novastore – Online Shopping Store

A complete, modern, professional full-stack Online Shopping Store application built with **React + Vite** on the frontend, **Python Flask + SQLAlchemy** on the backend, and **SQLite** for relational database persistence.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Architecture & Project Structure](#architecture--project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
7. [Database Setup & Seeding](#database-setup--seeding)
8. [Running the Application](#running-the-application)
9. [Automated Testing](#automated-testing)
10. [REST API Documentation](#rest-api-documentation)
11. [Screenshots Checklist](#screenshots-checklist)
12. [Security & Reliability](#security--reliability)
13. [Assumptions & Limitations](#assumptions--limitations)
14. [Future Enhancements](#future-enhancements)
15. [Contributors](#contributors)

---

## Project Overview

**Novastore** is an end-to-end e-commerce web platform engineered with beginner-friendly code clarity and senior-level architectural rigor. The application implements zero-trust pricing validation, atomic database transactions with rollback, inventory tracking, a centralized shopping cart with `localStorage` persistence, and an Indian-context validated checkout flow.

---

## Key Features

### A. Product Catalogue & Discovery
- **Dynamic Catalogue**: Displays products with high-resolution imagery, titles, descriptions, categories, prices, and stock statuses (`In Stock`, `Only X Left`, `Out of Stock`).
- **Real-Time Search**: Debounced substring search matching product titles and keywords.
- **Category Filter Chips**: Dynamic category aggregation with live item counts fetched from the backend.
- **Price Range Filtering**: Numerical minimum and maximum price filtering with strict boundary validation (`min_price <= max_price`).
- **Sorting Options**: Sort by price (ascending/descending), product name (A–Z / Z–A), and featured/newest.
- **Product Details Modal**: Deep-dive specification view showing item SKU, availability, overview, and quick-add quantity selector.

### B. Shopping Cart & Inventory Management
- **Centralized Cart State**: React Context (`CartContext`) managing items, quantities, and pricing calculations.
- **`localStorage` Persistence**: Cart contents automatically persist across page reloads and browser sessions.
- **Strict Stock Boundaries**: Prevents adding out-of-stock items and prevents cart quantities from exceeding live warehouse stock.
- **Quantity Steppers**: Increment (`+`) and decrement (`–`) controls ensuring positive integer quantities.
- **Real-Time Financial Calculations**: Computes line totals, order subtotal, dynamic delivery fee (Free for orders $\ge \$100$; otherwise flat $\$5.00$), and estimated total amount.
- **Cart Management**: Individual item removal, "Clear Cart" action, and an empty-cart state with a "Continue Shopping" CTA.

### C. Checkout & Validation
- **Responsive Checkout Form**: Collects customer full name, email address, mobile phone number, street address, city, and postal code.
- **Indian-Context Validation**:
  - Full Name: Required, 2–120 characters.
  - Email: Standard RFC-compliant format regex.
  - Phone Number: 10-digit Indian mobile number (`^(?:\+91)?[6-9]\d{9}$`).
  - Postal Code: 6-digit Indian PIN code (`^\d{6}$`).
- **Inline Field Feedback**: Clear, instant error messages beneath invalid inputs.
- **Simulated Payment**: Safe, mock transaction notice reassuring users that no real credit card or debit card is charged.

### D. Order Processing & Transaction Safety
- **Zero-Trust Pricing Architecture**: The backend never trusts prices, subtotals, or delivery fees submitted by the client. Canonical prices and stock levels are always fetched directly from the database.
- **Atomic Database Transactions**: Orders and order items are inserted, and stock is decremented within an atomic transaction. Any exception triggers an immediate `db.session.rollback()`.
- **Unique Order Reference**: Collision-tested order references formatted as `ORD-YYYYMMDD-XXXX`.
- **Purchase Snapshots**: Product names and unit prices are saved as immutable purchase-time snapshots in `order_items`.
- **Cart Protection on Failure**: The shopping cart is cleared **only** after the backend returns HTTP 201 Created. If validation or order placement fails, cart items are preserved.

### E. Order Confirmation & Receipts
- **Confirmation Screen**: Displays a confirmation checkmark, unique order reference, customer delivery information, order status (`CONFIRMED`), timestamp, itemized product table, and pricing breakdown.
- **Interactive Tools**: Single-click "Copy Code" reference button, "Print Receipt" (`window.print()`), and "Continue Shopping" button.

### F. Secure Admin Dashboard & Inventory Operations
- **Server-Side Authentication**: Secure login using Werkzeug cryptographic password hashing (`scrypt/pbkdf2`) and signed timestamped bearer tokens (`itsdangerous`).
- **Access Control & Protected APIs**: Every administrative endpoint is strictly guarded with the `@admin_required` decorator. Ordinary visitors cannot perform administrative mutations.
- **Executive Overview**: High-level KPI metric cards displaying total products, active catalogue items, total customer orders, total recorded warehouse inventory, and gross sales.
- **Order Fulfillment Breakdown**: Status breakdown pill metrics and recent customer order feeds.
- **Product Inventory Management**:
  - Full catalogue table viewing all 30 products with status badges (`Active` / `Inactive`).
  - Search by title or SKU and filter by category or stock condition.
  - "Add Product" and "Edit Product" modal dialogs with strict client and server validation.
  - Inline stock steppers (`+` / `–`) allowing rapid inventory count adjustments.
  - Safe Product Deletion: When an admin deletes a product with order history, it is **safely deactivated** (`is_active = False`) from the storefront rather than destroyed, preserving customer purchase invoices and database integrity.
- **Order Management & Status Tracking**:
  - Live order search by customer name, email, phone, or order reference.
  - Filter orders by status (`PENDING`, `CONFIRMED`, `SHIPPED`, `DELIVERED`, `CANCELLED`).
  - Deep-dive Order Details Modal displaying customer details, shipping address, purchase-time product snapshots, and line totals.
  - Controlled status updater transitioning orders between lifecycle stages with real-time feedback.
- **Storefront & Admin Portals**: Single-click seamless navigation between the public customer storefront and administrator dashboard.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, Vite 6, JavaScript (ES Modules), Vanilla CSS (Custom Tokens, Inter Typography) |
| **Backend** | Python 3.13, Flask 3.1, Flask-SQLAlchemy 3.1, Flask-CORS 5.0, python-dotenv 1.2 |
| **Database** | SQLite 3 (with `PRAGMA foreign_keys=ON`) |
| **Testing** | Pytest 8.4 (Backend), Node.js Test Runner (Frontend) |
| **Version Control** | Git |

---

## Architecture & Project Structure

```text
D:\E-Commerce\
├── backend/
│   ├── app/
│   │   ├── models/
│   │   │   ├── __init__.py         # Model package exports
│   │   │   ├── db.py               # SQLAlchemy instance & SQLite foreign key PRAGMA
│   │   │   ├── product.py          # Product table schema & serialization
│   │   │   ├── order.py            # Order table schema & customer fields
│   │   │   └── order_item.py       # OrderItem snapshot schema & foreign keys
│   │   ├── routes/
│   │   │   ├── __init__.py         # Route blueprints export
│   │   │   ├── product_routes.py   # GET /api/products, /api/categories, /api/products/<id>
│   │   │   └── order_routes.py     # POST /api/orders, GET /api/orders/<reference>
│   │   ├── services/
│   │   │   ├── __init__.py         # Service layer exports
│   │   │   ├── product_service.py  # Product filtering, search, and sorting logic
│   │   │   └── order_service.py    # Order calculation, stock check, atomic transactions
│   │   ├── __init__.py             # Flask application factory (create_app) & CORS
│   │   ├── config.py               # Development, Testing, Production configurations
│   │   └── database.py             # Database creation and sample seed data
│   ├── instance/
│   │   └── store.db                # SQLite database file (untracked in Git)
│   ├── tests/
│   │   ├── conftest.py             # Pytest fixtures (:memory: SQLite database)
│   │   ├── test_app.py             # Application factory tests
│   │   ├── test_database.py        # Database seeding, foreign keys, and rollbacks
│   │   ├── test_models.py          # Model constraints and cascade deletes
│   │   ├── test_products_api.py    # Catalog, search, filter, and sorting tests
│   │   ├── test_orders_api.py      # Checkout and order creation tests
│   │   ├── test_edge_cases.py      # Concurrency, injection, phone/PIN edge cases
│   │   └── test_e2e_journey.py     # Complete 11-step end-to-end customer journey test
│   ├── pytest.ini                  # Backend pytest configuration
│   ├── requirements.txt            # Python dependencies
│   ├── run.py                      # Backend server runner (port 5000)
│   └── seed.py                     # Standalone database seed script
│
├── frontend/
│   ├── dist/                       # Vite production build output
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx          # Header with branding and live cart item badge
│   │   │   ├── Hero.jsx            # Value proposition header banner
│   │   │   ├── FilterBar.jsx       # Search input, category chips, price filter, sorting
│   │   │   ├── ProductCard.jsx     # Product card with stock badges and Add to Cart
│   │   │   ├── ProductDetailsModal.jsx # Full specifications modal with quantity selector
│   │   │   ├── LoadingState.jsx    # Animated loading spinner
│   │   │   ├── EmptyState.jsx      # Zero-results state with filter reset action
│   │   │   ├── NotificationToast.jsx # Slide-in toast alerts
│   │   │   └── Footer.jsx          # Professional footer
│   │   ├── context/
│   │   │   └── CartContext.jsx     # React Context for cart state & localStorage
│   │   ├── pages/
│   │   │   ├── CatalogPage.jsx     # Main catalogue view
│   │   │   ├── CartPage.jsx        # Shopping cart view with order summary
│   │   │   ├── CheckoutPage.jsx    # Checkout form with Indian validation
│   │   │   └── OrderConfirmationPage.jsx # Order receipt with reference code
│   │   ├── services/
│   │   │   └── api.js              # Reusable fetch client for Flask API
│   │   ├── App.jsx                 # View router and root layout
│   │   ├── main.jsx                # React root mount
│   │   └── style.css               # Vanilla CSS design system
│   ├── tests/
│   │   ├── api_client.test.mjs     # API client query string tests
│   │   ├── cart_logic.test.mjs     # Cart state, stock capping, and math tests
│   │   └── checkout_validation.test.mjs # Form validation and cart clearing tests
│   ├── index.html                  # HTML5 entry with Google Inter font
│   ├── package.json                # Frontend dependencies and scripts
│   └── vite.config.js              # Vite server & /api proxy to localhost:5000
│
├── .gitignore                      # Git exclusion rules (.venv, node_modules, *.db)
├── .env.example                    # Environment variable template
├── pytest.ini                      # Root pytest configuration
└── README.md                       # Complete project documentation
```

---

## Prerequisites

Ensure the following tools are installed on your workstation:

- **Python**: Version 3.13+ (or 3.9+)
- **Node.js**: Version 20+ (v24.14.0 recommended)
- **npm**: Version 10+ (v11.9.0 recommended)
- **Git**: Version 2.40+
- **Shell**: Windows PowerShell (or Bash on macOS/Linux)

---

## Installation & Setup

### 1. Clone or Open the Repository
```powershell
cd D:\E-Commerce
```

### 2. Backend Setup
Create and activate the virtual environment, then install dependencies:

```powershell
# Navigate to the backend directory
cd D:\E-Commerce\backend

# Activate the virtual environment
.\.venv\Scripts\Activate.ps1

# (Optional: create if not already present: python -m venv .venv)

# Install required dependencies
python -m pip install -r requirements.txt
```

### 3. Frontend Setup
Install frontend dependencies:

```powershell
# Navigate to the frontend directory
cd D:\E-Commerce\frontend

# Install node modules
npm install
```

---

## Database Setup & Seeding

The SQLite database file is stored in `backend/instance/store.db`.

To initialize the database schema and populate it with 30 sample products across 6 categories (Electronics, Audio, Accessories, Home & Office, Wearables, and Photography):

```powershell
# From D:\E-Commerce\backend
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

### Creating an Administrator Account

Administrator registration is strictly prohibited through public web endpoints. To provision an administrator, use either the standalone script or the Flask interactive CLI:

```powershell
# Option A: Standalone CLI Script (with command-line arguments)
cd D:\E-Commerce\backend
.\.venv\Scripts\Activate.ps1
python create_admin.py --username admin --email admin@example.com --password YourSecurePassword123!

# Option B: Interactive CLI Command (prompts for masked password)
flask --app run.py create-admin
```

---

## Running the Application

Run the backend and frontend in two separate terminal windows:

### Terminal 1: Backend Server (Flask API)
```powershell
cd D:\E-Commerce\backend
.\.venv\Scripts\Activate.ps1
python run.py
```
- The backend REST API will start on: **`http://127.0.0.1:5000`**
- Health check route: **`http://127.0.0.1:5000/api/health`**

### Terminal 2: Frontend Server (Vite React)
```powershell
cd D:\E-Commerce\frontend
npm run dev
```
- The frontend will be accessible at: **`http://localhost:5173`**
- API requests made to `/api/*` are automatically proxied to `http://127.0.0.1:5000`.

---

## Automated Testing

### 1. Backend Pytest Suite (69 Tests)
The backend tests run against an isolated in-memory SQLite database (`sqlite:///:memory:`) and never modify your development database.

```powershell
# Run from repository root or backend folder
cd D:\E-Commerce
& .\backend\.venv\Scripts\python.exe -m pytest -v
```

*Expected Result:*
```text
============================= 69 passed in 3.40s ==============================
```

#### Test Suite Breakdown:
- **`tests/test_admin_api.py`** (19 tests): Administrator login, email auth, invalid credentials, token verification, unauthorized access, dashboard stats, product creation/updating, safe soft-deletion preserving historical order items, orders list/filtering, and status transitions.
- **`tests/test_app.py`** (1 test): Application factory and development configurations.
- **`tests/test_database.py`** (5 tests): Seeding idempotency, transaction rollbacks, and SQLite `PRAGMA foreign_keys=ON`.
- **`tests/test_models.py`** (4 tests): Non-negative price/stock check constraints, cascade deletions, and purchase snapshot retention.
- **`tests/test_products_api.py`** (19 tests): Catalogue retrieval, 30 products assertion, 6 categories including Photography, category filters, price ranges, sort orders, product details, and safe idempotent seeding.
- **`tests/test_orders_api.py`** (12 tests): Checkout creation, customer validation, quantity checks, price tamper resistance, delivery fee rules, and reference lookup.
- **`tests/test_edge_cases.py`** (8 tests): Reference format uniqueness, duplicate product ID aggregation, sequential stock depletion, Indian phone/PIN validation, and SQL injection safety.
- **`tests/test_e2e_journey.py`** (1 test): Full 11-step customer shopping journey from browsing to database inventory deduction.

---

### 2. Frontend Automated Tests (25 Tests)
Runs natively using the Node.js test runner:

```powershell
cd D:\E-Commerce\frontend
npm test
```

*Expected Result:*
```text
✔ Admin Dashboard Frontend Logic Tests (8 tests)
✔ Frontend API Client Tests (5 tests)
✔ Shopping Cart Logic & State Tests (7 tests)
✔ Checkout Validation & Order Flow Tests (5 tests)
ℹ tests 25 | pass 25 | fail 0
```

---

### 3. Frontend Production Build
To verify that the application compiles cleanly for production:

```powershell
cd D:\E-Commerce\frontend
npm run build
```

*Expected Result:*
```text
✓ 52 modules transformed.
dist/index.html                   0.84 kB │ gzip:  0.46 kB
dist/assets/index-2sM-HN-3.css   45.13 kB │ gzip:  7.69 kB
dist/assets/index-Dxq1gBQa.js   307.49 kB │ gzip: 87.65 kB
✓ built in ~1s
```

---

## REST API Documentation

### 1. `GET /api/products`
Retrieve catalogue products with optional search, category, price bounds, and sorting.

**Query Parameters:**
- `search` (string): Search term matching product names.
- `category` (string): Filter by category name (e.g. `Electronics`, `Audio`).
- `min_price` (float): Minimum price.
- `max_price` (float): Maximum price.
- `sort` (string): `price_asc`, `price_desc`, `name_asc`, `name_desc`, or `newest`.

**Sample Response (HTTP 200 OK):**
```json
{
  "count": 12,
  "filters": {
    "category": "Electronics",
    "max_price": 100.0,
    "min_price": 40.0,
    "search": null,
    "sort": "price_asc"
  },
  "products": [
    {
      "id": 2,
      "name": "Precision Ergonomic Optical Mouse",
      "category": "Electronics",
      "price": 49.50,
      "stock_quantity": 40,
      "description": "Contoured ergonomic wireless mouse with silent clicks...",
      "image_path": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?...",
      "created_at": "2026-11-01T15:09:03.123456",
      "updated_at": "2026-11-01T15:09:03.123456"
    }
  ]
}
```

---

### 2. `GET /api/products/<int:id>`
Retrieve complete details of a specific product.

**Sample Response (HTTP 200 OK):**
```json
{
  "id": 1,
  "name": "Ultra-Slim Wireless Mechanical Keyboard",
  "category": "Electronics",
  "price": 89.99,
  "stock_quantity": 24,
  "description": "Low-profile mechanical switches with RGB backlighting...",
  "image_path": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?...",
  "created_at": "2026-11-01T15:09:03.123456",
  "updated_at": "2026-11-01T15:09:03.123456"
}
```

---

### 3. `GET /api/categories`
Retrieve all available categories and product counts.

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

### 4. `POST /api/orders`
Place a new order with simulated checkout.

**Request Body:**
```json
{
  "customer_name": "Priya Patel",
  "customer_email": "priya.patel@example.com",
  "customer_phone": "9876543210",
  "delivery_address": "Sector 14, Hiranandani Estate",
  "city": "Thane",
  "postal_code": "400607",
  "items": [
    { "product_id": 1, "quantity": 1 },
    { "product_id": 2, "quantity": 2 }
  ]
}
```

**Sample Response (HTTP 201 Created):**
```json
{
  "message": "Order placed successfully",
  "order": {
    "id": 1,
    "order_reference": "ORD-20261101-CDB0",
    "customer_name": "Priya Patel",
    "customer_email": "priya.patel@example.com",
    "customer_phone": "9876543210",
    "delivery_address": "Sector 14, Hiranandani Estate",
    "city": "Thane",
    "postal_code": "400607",
    "subtotal": 188.99,
    "delivery_fee": 0.0,
    "total_amount": 188.99,
    "status": "CONFIRMED",
    "created_at": "2026-11-01T15:38:53.242629",
    "items": [
      {
        "id": 1,
        "order_id": 1,
        "product_id": 1,
        "product_name": "Ultra-Slim Wireless Mechanical Keyboard",
        "unit_price": 89.99,
        "quantity": 1,
        "line_total": 89.99
      },
      {
        "id": 2,
        "order_id": 1,
        "product_id": 2,
        "product_name": "Precision Ergonomic Optical Mouse",
        "unit_price": 49.50,
        "quantity": 2,
        "line_total": 99.00
      }
    ]
  }
}
```

---

### 5. `GET /api/orders/<string:reference>`
Fetch an order's confirmation details by its reference.

**Sample Response (HTTP 200 OK):**
```json
{
  "order": {
    "order_reference": "ORD-20261101-CDB0",
    "status": "CONFIRMED",
    "customer_name": "Priya Patel",
    "customer_email": "priya.patel@example.com",
    "customer_phone": "9876543210",
    "delivery_address": "Sector 14, Hiranandani Estate",
    "city": "Thane",
    "postal_code": "400607",
    "subtotal": 188.99,
    "delivery_fee": 0.0,
    "total_amount": 188.99,
    "created_at": "2026-11-01T15:38:53.242629",
    "items": []
  }
}
```

---

### 6. Administrator API Endpoints (Protected: Bearer Token Required)

All endpoints below require an `Authorization: Bearer <token>` header obtained from `/api/admin/login`.

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/admin/login` | Authenticate admin credentials and issue bearer token. |
| `POST` | `/api/admin/logout` | Terminate administrator session. |
| `GET` | `/api/admin/me` | Verify token validity and fetch authenticated profile. |
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

## Screenshots Checklist

When preparing project submission media, capture the following application views:

- [ ] **1. Storefront & Product Catalogue**: Default landing page showing the modern navigation bar, live cart count badge, hero banner, category chips, and product grid.
- [ ] **2. Search & Filtering in Action**: Products filtered by category (e.g. `Audio`, `Photography`) and sorted by price.
- [ ] **3. Product Details Modal**: Open modal showcasing product specifications, category tag, live stock status, and quantity stepper.
- [ ] **4. Shopping Cart Page**: Cart view displaying items with line totals, quantity controls (`+` / `–`), subtotal, dynamic free delivery hint, and order summary.
- [ ] **5. Empty Cart State**: View displayed when all items are cleared from the cart with the "Explore Catalog" CTA.
- [ ] **6. Checkout Page**: Shipping form with customer inputs, Indian phone and PIN validation indicators.
- [ ] **7. Order Confirmation Page**: Complete receipt screen showing the green success badge, unique order reference (`ORD-YYYYMMDD-XXXXXXXX`), and itemized purchase snapshot table.
- [ ] **8. Admin Login Portal**: Secure authentication screen with username/email and password fields.
- [ ] **9. Admin Executive Overview**: Dashboard KPI metrics cards, status breakdown pills, and recent customer orders table.
- [ ] **10. Admin Product Inventory**: Full 30-item table with status badges, inline stock adjusters, and Add/Edit modal.
- [ ] **11. Admin Order Fulfillment**: Orders table with status filters and detailed Order Details Modal with purchase snapshots.
- [ ] **12. Terminal & Passing Tests**: Terminal showing all 69 backend tests passing and 25 frontend tests passing.


---

## Security & Reliability

- **SQL Injection Prevention**: Parameterized queries via SQLAlchemy ORM; checked against SQL injection inputs.
- **Zero-Trust Pricing**: All totals, subtotals, and delivery charges are calculated exclusively on the backend from database prices. Frontend prices are disregarded.
- **Concurrency & Stock Integrity**: Orders are validated against live warehouse inventory; database transactions guarantee that partial order failures roll back completely without stock leakage.
- **Environment Separation**: Test database is strictly in-memory (`:memory:`), preventing test runs from corrupting development databases.
- **Information Disclosure Protection**: Error handlers return clean JSON error messages and suppress stack traces in production.

---

## Assumptions & Limitations

- **Simulated Checkout**: Real credit card and payment gateway integration (e.g. Stripe, Razorpay) is omitted by design for this academic/portfolio project.
- **Single Currency**: All prices are represented and calculated in USD (`$`).
- **SQLite Database**: SQLite is utilized for simple setup. In a multi-instance production environment, PostgreSQL or MySQL would be used for higher concurrent write throughput.
- **Local Storage Cart**: Shopping cart data is stored in browser `localStorage`. Cart contents are specific to the user's browser until order checkout.

---

## Future Enhancements

- [ ] User authentication with JWT (JSON Web Tokens) or session cookies for customer profiles and past order histories.
- [ ] Payment gateway integration with Razorpay, Stripe, or PayPal webhooks.
- [ ] Admin dashboard for inventory restocking, adding new catalog items, and managing shipments.
- [ ] Automated email confirmations sent via SendGrid or AWS SES upon order creation.
- [ ] Real-time product search with algorithmic typo tolerance and fuzzy matching.

---

## Contributors

- **Author**: *[Your Name / GitHub Profile]*
- **Project**: Novastore Full-Stack Online Shopping Store
- **License**: MIT License
