# NovaStore — Deployment & Infrastructure Guide

This guide details the production deployment architecture, hosting platforms, environment variables, release procedures, and operational smoke tests for NovaStore.

---

## 1. Production Architecture Overview

NovaStore uses a multi-cloud production architecture:

| Component | Platform | URL / Host | Purpose |
| :--- | :--- | :--- | :--- |
| **Frontend** | Vercel | `https://novastore-tau.vercel.app` | Global CDN hosting, static asset delivery, and API reverse proxy rewrite. |
| **Backend** | Render | `https://novastore-api-2w65.onrender.com` | Linux Web Service running Gunicorn WSGI and Python 3.13 Flask application. |
| **Database** | Neon Cloud | Managed PostgreSQL | Managed serverless PostgreSQL database with SSL enforcement. |

---

## 2. Vercel Frontend Deployment

### A. Project Configuration
- **Framework Preset:** Vite
- **Root Directory:** `frontend`
- **Build Command:** `npm run build`
- **Output Directory:** `dist`
- **Install Command:** `npm install`
- **Node.js Version:** `20.x` or higher

### B. API Rewrite Configuration (`frontend/vercel.json`)
The frontend uses Vercel URL rewrites to proxy all API requests to the Render backend service transparently. This eliminates browser cross-origin cookie restrictions and allows `SameSite=Strict` cookies to operate smoothly:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://<your-render-api-subdomain>.onrender.com/api/$1"
    },
    {
      "source": "/(.*)",
      "destination": "/index.html"
    }
  ]
}
```

---

## 3. Render Backend Deployment

### A. Service Settings
- **Service Type:** Web Service
- **Runtime:** Python 3
- **Root Directory:** `backend`
- **Branch:** `main`
- **Auto-Deploy:** Configured in the Render dashboard (recommended to disable auto-deploy on push to allow explicit preflight verification prior to deployment).
- **Hosting Region:** Dashboard-managed (configured to match or minimize latency to the Neon cloud PostgreSQL instance).
- **Build Command:**
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command:**
  ```bash
  gunicorn run:app
  ```

---

## 4. Environment Variables Matrix

### A. Production Environment Variables (Render Backend)

| Variable | Required? | Example Format / Constraint | Description |
| :--- | :---: | :--- | :--- |
| `FLASK_ENV` | **Yes** | `production` | Enforces production security checks, strict CORS, and disables debug mode. |
| `SECRET_KEY` | **Yes** | 64-char hex string | Cryptographic key used to sign session cookies and tokens. Must be $\ge 32$ random characters. Generation: `python -c "import secrets; print(secrets.token_hex(32))"`. Startup fails if missing or default. |
| `DATABASE_URL` | **Yes** | `postgresql://user:pass@host/db?sslmode=require` | Connection URI for Neon PostgreSQL. Normalized to `postgresql+psycopg2://` by backend. Startup fails if missing or using SQLite in production mode. |
| `CORS_ORIGINS` | **Yes** | `https://novastore-tau.vercel.app` | Comma-separated list of authorized client origins. Wildcard `*` is strictly forbidden in production. |
| `TRUSTED_PROXIES_COUNT` | **Yes** | `1` (or matching proxy chain) | Exact count of upstream reverse proxies forwarding traffic to Werkzeug's `ProxyFix`. Must match the verified infrastructure proxy chain to prevent IP spoofing. |
| `PORT` | Optional | `5000` (Render sets automatically) | TCP port on which Gunicorn listens. |
| `RATELIMIT_ENABLED` | Optional | `True` | Toggles in-memory rate limiting (default: `True`). |
| `RATELIMIT_ADMIN_LOGIN_LIMIT` | Optional | `5` | Maximum admin login attempts per client IP window (default: 5; legacy alias `RATELIMIT_LOGIN_LIMIT` supported). |
| `RATELIMIT_ADMIN_LOGIN_PERIOD` | Optional | `60` | Admin login sliding-window duration in seconds (default: 60; legacy alias `RATELIMIT_LOGIN_PERIOD` supported). |
| `RATELIMIT_ORDER_CREATE_LIMIT` | Optional | `10` | Maximum order submissions per client IP window (default: 10; legacy alias `RATELIMIT_ORDER_LIMIT` supported). |
| `RATELIMIT_ORDER_CREATE_PERIOD` | Optional | `60` | Order submission sliding-window duration in seconds (default: 60; legacy alias `RATELIMIT_ORDER_PERIOD` supported). |

> [!WARNING]
> Never commit real database connection strings, passwords, or production secret keys to version control. Set these exclusively in platform secret managers.

### B. Local Development Variables (`backend/.env`)

| Variable | Value for Local Dev | Purpose |
| :--- | :--- | :--- |
| `FLASK_ENV` | `development` | Enables interactive debugging and relaxed CORS. |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | Safe development fallback key. |
| `DATABASE_URL` | `sqlite:///instance/store.db` | Points to local SQLite database file. |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allows local Vite frontend servers. |
| `TRUSTED_PROXIES_COUNT` | `0` | Disables ProxyFix for local direct connections. |

---

## 5. Deployment Procedures

### A. Pre-Deployment Verification
Before deploying new changes to production, execute the automated verification test suites locally:

1. **Verify Git Tree:** Ensure working tree is clean on branch `main`:
   ```powershell
   git status
   ```
2. **Run Backend Test Suite:**
   ```powershell
   cd D:\E-Commerce
   & .\backend\.venv\Scripts\python.exe -m pytest backend
   ```
3. **Run Frontend Test Suite:**
   ```powershell
   cd D:\E-Commerce\frontend
   npm test
   ```
4. **Compile Frontend Production Build:**
   ```powershell
   npm run build
   ```

### B. Deployment Execution
1. Push verified commits to the GitHub repository:
   ```powershell
   git push origin main
   ```
2. **Backend Deployment (Render):**
   - Open the Render Dashboard for `novastore-api`.
   - Verify that all environment variables are present and up to date.
   - Click **Manual Deploy** ➔ **Deploy latest commit**.
   - Monitor the deploy logs until `Listening at: http://0.0.0.0:<PORT>` is reached.
3. **Frontend Deployment (Vercel):**
   - Vercel automatically deploys commits to `main`.
   - Verify build status in the Vercel dashboard and confirm production alias points to the latest deployment.

---

## 6. Post-Deployment Smoke Tests

Execute read-only smoke tests against production endpoints immediately after deployment:

```powershell
# 1. Verify backend health check
curl -I https://novastore-api-2w65.onrender.com/api/health

# 2. Verify Vercel frontend proxy rewrite
curl -s https://novastore-tau.vercel.app/api/health

# 3. Verify public product catalogue (should return 30 items)
curl -s https://novastore-tau.vercel.app/api/products

# 4. Verify category listing (should return 6 categories)
curl -s https://novastore-tau.vercel.app/api/categories

# 5. Verify unauthenticated administrative protection (must return HTTP 401)
curl -I https://novastore-tau.vercel.app/api/admin/me
curl -I https://novastore-tau.vercel.app/api/admin/stats
```

---

## 7. Rollback & Disaster Recovery Precautions

1. **Backend Rollback:**
   - In Render Dashboard ➔ **Deploys**, select the previous stable deployment and click **Rollback**.
2. **Frontend Rollback:**
   - In Vercel Dashboard ➔ **Deployments**, locate the last verified working build and click **Promote to Production**.
3. **Database Safeguards:**
   - Neon PostgreSQL provides instantaneous point-in-time branch creation and snapshots. Prior to applying database schema changes or migrations, take a snapshot branch in the Neon console.
   - Keep local timestamped SQLite backups using `python backend/create_backup.py`.
