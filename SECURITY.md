# NovaStore — Security Policy & Architectural Hardening

This document outlines the security controls, authentication mechanisms, threat mitigations, and documented limitations implemented across NovaStore.

---

## 1. Authentication & Session Management

### A. Administrator Password Hashing
- Administrator passwords are hashed using Werkzeug's cryptographic security utilities (`generate_password_hash` / `check_password_hash`), utilizing modern algorithms (e.g., `scrypt` or `pbkdf2:sha256`) with automatic per-user salt generation.
- **Password Policy:** A minimum length of 8 characters is strictly enforced across interactive CLI prompts, environment variables, and password rotation utilities.

### B. Session Cookies
- Upon successful administrative login, session tokens are issued inside an `admin_session` cookie:
  - `HttpOnly = True`: Inaccessible via JavaScript APIs (`document.cookie`), mitigating the risk of token exfiltration via Cross-Site Scripting (XSS).
  - `SameSite = "Strict"`: Browser will not send the session cookie on cross-site requests, protecting against Cross-Site Request Forgery (CSRF).
  - `Secure = True`: Enforced automatically in production to guarantee transmission strictly across encrypted HTTPS connections.
  - `Max-Age = 7200`: Sessions expire after 2 hours.
- Session tokens are generated using `itsdangerous.URLSafeTimedSerializer` signed with the server's `SECRET_KEY`.

### C. Token Revocation
- When an administrator rotates their password (`python rotate_admin_password.py`), the `updated_at` timestamp on the admin record is updated.
- The authentication middleware verifies the token timestamp against the database; any tokens generated before the `updated_at` timestamp are immediately rejected, effectively invalidating all active sessions across all devices.

---

## 2. Cross-Site Request Forgery (CSRF) Protection

- In addition to `SameSite=Strict` cookie policies, NovaStore implements the **Synchronizer Token Pattern** for state-changing administrative operations (`POST`, `PUT`, `PATCH`, `DELETE`).
- The login endpoint issues a cryptographically tied CSRF token in an un-httponly `csrf_token` cookie and JSON response body.
- The frontend client extracts this token and transmits it in the `X-CSRF-Token` request header on mutating API requests.
- The backend verifies that the header token matches the active session token before allowing data modifications.

---

## 3. Network & Origin Hardening

### A. Cross-Origin Resource Sharing (CORS)
- In development, CORS origins default to local development servers (`http://localhost:5173,http://127.0.0.1:5173`).
- In production, explicit origins must be configured in `CORS_ORIGINS`.
- **Production Fail-Safe:** The application strictly aborts startup if `CORS_ORIGINS` is missing or contains a wildcard (`*`).
- `supports_credentials=True` is enabled to permit authenticated session cookies across allowed origins.

### B. Production Secret Key Enforcement
- The backend startup routine inspects `SECRET_KEY`.
- If running in production mode, startup immediately raises a `RuntimeError` if:
  1. `SECRET_KEY` is not set or empty.
  2. `SECRET_KEY` matches known insecure development defaults (`dev-secret-key-change-in-production`).
  3. `SECRET_KEY` is shorter than 32 characters.

### C. Trusted Reverse Proxy Handling (`ProxyFix`)
- Render, Vercel, and cloud load balancers route incoming traffic through reverse proxy layers.
- NovaStore configures Werkzeug's `ProxyFix` middleware based on the `TRUSTED_PROXIES_COUNT` environment variable:
  - When `TRUSTED_PROXIES_COUNT = 0` (default), `ProxyFix` is disabled, and `request.remote_addr` is read directly, preventing attackers from spoofing their IP address using untrusted `X-Forwarded-For` headers.
  - When `TRUSTED_PROXIES_COUNT > 0`, `ProxyFix` securely unwraps only the specified number of trusted hops.

---

## 4. Rate Limiting Architecture

- Sensitive endpoints are protected by an in-memory sliding-window rate limiter (`InMemoryRateLimiter`):
  - `POST /api/admin/login`: Defaults to 5 requests per 60 seconds per IP address to defend against brute-force and credential-stuffing attacks.
  - `POST /api/orders`: Defaults to 10 requests per 60 seconds per IP address to mitigate automated order flooding.
- Exceeding the rate limit returns `HTTP 429 Too Many Requests` with a calculated `Retry-After` header.

---

## 5. Transaction Safety & Zero-Trust Pricing

### A. Zero-Trust Financial Recalculation
- The client cannot dictate product prices, subtotals, or delivery fees.
- When an order payload is received, the backend fetches canonical product prices directly from the database, re-computes subtotal and delivery fee, and asserts all constraints authoritatively.

### B. Database Constraints & Atomic Rollback
- Relational check constraint: `check_product_stock_non_negative` enforces `stock_quantity >= 0` at the database engine level in PostgreSQL.
- Stock decrementing, order item record creation, and order header insertion occur within a single database transaction.
- If inventory is insufficient or an exception occurs during order processing, `db.session.rollback()` is invoked immediately, preventing inventory leakage or partial order commits.

---

## 6. Documented Limitations & Threat Model

While NovaStore implements defense-in-depth measures, the following limitations are explicitly documented:

1. **In-Memory Rate Limiting (Single-Process Scope):**
   - The built-in rate limiter stores sliding-window timestamps in Python memory (`threading.Lock`).
   - In production deployments running multiple Gunicorn worker processes or horizontally scaled container instances, rate-limit buckets are independent per worker and not synchronized via a shared cache (such as Redis).
2. **Simulated Payment Gateway:**
   - NovaStore does not integrate a real payment gateway (such as Stripe, Razorpay, or PayPal).
   - Checkout is simulated (Cash on Delivery / Direct confirmation). No credit card numbers, CVVs, or financial credentials are collected or processed.
3. **Checkout Idempotency:**
   - The checkout route does not implement idempotency keys. If a client submits rapid duplicate requests, the server relies on rate limiting and database constraints rather than deduplication tokens.
4. **Concurrent Stock Contention:**
   - Under extremely high concurrent checkout volume for the last unit of stock, the losing transaction triggers a database check constraint rollback (`InsufficientStockError`), which currently returns `HTTP 400 Bad Request` rather than a queue-based retry mechanism.
