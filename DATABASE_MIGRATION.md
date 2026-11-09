# NovaStore — Database Migration Guide

This document describes the database migration architecture, tools, safety protocols, and verification procedures used to migrate NovaStore from the local SQLite database to the production Neon PostgreSQL cloud database.

---

## 1. Overview & Database Roles

| Environment | Database System | File / Host | Role |
| :--- | :--- | :--- | :--- |
| **Development** | SQLite 3 | `backend/instance/store.db` | Local development and automated testing database. |
| **Testing** | SQLite 3 | `:memory:` | Isolated in-memory database used by Pytest test runs. |
| **Production** | PostgreSQL 16+ | Neon Managed Cloud | High-availability cloud PostgreSQL database for the live store. |

---

## 2. Migration Tool Architecture

The migration tool is located at:
```text
backend/scripts/migrate_sqlite_to_postgres.py
```

It is a standalone, transaction-safe migration engine engineered with zero-trust validation and strict rollback guarantees.

### Key Guarantees & Safeguards
1. **Source Read-Only Integrity:**
   - Opens SQLite strictly with the read-only URI flag (`file:...?...mode=ro`, `uri=True`).
   - Verifies the SHA-256 checksum of the SQLite source database before processing.
   - Never deletes, updates, or modifies the local SQLite database.
2. **Default Dry-Run Mode:**
   - Dry-run is the default execution mode.
   - In dry-run mode, no connection to the target database is opened, no target engine is instantiated, and no tables or records are modified.
   - Performing target schema creation and data copying strictly requires the explicit `--execute` CLI flag.
3. **Single Atomic Transaction:**
   - All table migrations (products, orders, order items, administrators, revoked tokens) execute inside a single atomic transaction.
   - If any record divergence, constraint violation, or sequence error occurs, the entire transaction is rolled back immediately via `session.rollback()`.
4. **Exact Precision Preservation:**
   - Preserves exact source strings, including formatting and whitespace.
   - Preserves exact numeric amounts without float truncation.
   - Converts datetimes to UTC timezone-aware objects with microsecond precision.
5. **Transactional Sequence Synchronization:**
   - In PostgreSQL, primary keys backed by identity sequences must be synchronized after copying records with explicit primary keys.
   - The migration script synchronizes sequences using transactional `ALTER SEQUENCE <seq> RESTART WITH <next_val>` statements.
   - Sequence synchronization occurs **inside the active data transaction before commit**. If sequence synchronization fails, all data is rolled back.
6. **SSL Enforcement & Credential Masking:**
   - Enforces `sslmode=require` on the target PostgreSQL connection. Insecure modes (`disable`, `allow`, `prefer`) are strictly rejected.
   - Logs and console output automatically redact passwords, database credentials, and connection strings.

---

## 3. Migration Procedure

### A. Preflight Safeguards
1. **Source Backup:** Create a timestamped backup of the local SQLite database before running migration operations:
   ```powershell
   cd D:\E-Commerce\backend
   .\.venv\Scripts\Activate.ps1
   python create_backup.py
   ```
2. **Neon Cloud Snapshot:** Take a point-in-time snapshot or branch of the target Neon database in the cloud console.

### B. Step 1: Execute Dry-Run Validation
Run the script without flags to validate source integrity and review intended migration operations without touching the target database:

```powershell
cd D:\E-Commerce\backend
.\.venv\Scripts\Activate.ps1
python scripts/migrate_sqlite_to_postgres.py
```

*Expected Dry-Run Behavior:*
- Verifies source SQLite integrity and row counts.
- Displays table-by-table migration summaries.
- Confirms that target database connections are blocked in dry-run mode.

### C. Step 2: Execute Migration (Authorized Production Runs Only)
To execute the migration against the target database, set the target PostgreSQL connection string in the environment and provide the explicit `--execute` flag:

```powershell
$env:TARGET_DATABASE_URL="postgresql://user:password@host/database?sslmode=require"
python scripts/migrate_sqlite_to_postgres.py --execute
Remove-Item Env:\TARGET_DATABASE_URL
```

---

## 4. Dual-Currency Data Integrity

NovaStore maintains dual-currency support within the same relational schema:

1. **Current Catalogue:** Products are priced and transacted in Indian Rupees (`currency="INR"`, symbol `₹`).
2. **Historical Orders:** Pre-migration orders created in US Dollars retain their original currency code (`currency="USD"`) and purchase-time line item snapshots.
3. **Immutability:** Migration guarantees that historical USD order records and totals are not converted or rounded, preserving accurate historical invoices.

---

## 5. Post-Migration Verification Checklist

After running the migration, verify target database health:

- [ ] Connect to PostgreSQL with read-only permissions.
- [ ] Confirm row counts match the expected catalogue size (30 products across 6 categories).
- [ ] Confirm historical orders and recent orders are present with correct `currency` codes and `status` values.
- [ ] Verify sequence state: inserting a test record increments primary keys without collision errors (`nextval`).
- [ ] Verify that foreign keys (`order_items.order_id ➔ orders.id`, `order_items.product_id ➔ products.id`) are enforced.
- [ ] Verify that table constraints (`check_product_stock_non_negative`) are enforced.

---

## 6. Disaster Recovery & Rollback

If a target migration fails or is interrupted:
1. Because the script executes inside an atomic transaction, any failure triggers an automatic `ROLLBACK`, leaving target tables uncommitted.
2. In the event of an unexpected partial target state, restore the Neon database to the pre-migration snapshot branch via the Neon cloud console.
3. The source SQLite database (`backend/instance/store.db`) remains completely untouched and read-only throughout all migration steps.
