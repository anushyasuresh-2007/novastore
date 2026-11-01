# Online Shopping Store

A full-stack online shopping store starter project. The frontend and backend are kept in separate folders. Store features and SQLite persistence have not been implemented yet.

## Technology

- Frontend: React and Vite (Node.js 18+)
- Backend: Flask (Python 3.9+)
- Database: SQLite, available through Python's standard library
- Tests: pytest

The project has been scaffolded with Python 3.13.14. Flask 3.1 and pytest 8.3 support Python 3.13.

## Project structure

```text
frontend/                 React + Vite starter
  src/
backend/
  app/                    Flask application package
  tests/                  pytest tests
  .venv/                  Local Python virtual environment (not tracked)
README.md
.gitignore
```

## Set up the backend (Windows PowerShell)

The virtual environment is created at `backend\.venv`. Activate it and install the backend dependencies:

```powershell
.\backend\.venv\Scripts\Activate.ps1
python -m pip install -r .\backend\requirements.txt
python -m pytest .\backend\tests
```

## Set up the frontend

Install dependencies and start the Vite development server:

```powershell
cd .\frontend
npm install
npm run dev
```

## Next steps

Implement the REST API and persistent SQLite storage for products, stock, and orders in a later development step. No application features, API routes, or database schema are included in this scaffold.
