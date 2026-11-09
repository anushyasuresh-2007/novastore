#!/usr/bin/env python3
"""
NovaStore — SQLite to Neon PostgreSQL Safe Migration Script
============================================================
Safely transfers live store data from the validated SQLite source
(`backend/instance/store.db`) to the target PostgreSQL database (Neon).

Core Guarantees & Safeguards:
1. STRICT SOURCE INTEGRITY:
   - Opens SQLite strictly in read-only mode (`file:...?...mode=ro`, `uri=True`).
   - Verifies SHA-256 source database checksum against baseline.
   - Verifies expected row counts before touching target database.
   - Never deletes, updates, or alters SQLite files or backups.

2. CRITICAL DRY-RUN ISOLATION:
   - Default mode is DRY-RUN.
   - In dry-run mode, NO target engine is created, NO target connection is opened,
     and NO target tables, sequences, or records are touched.
   - Target database connection, DDL schema creation (`create_all`), and writes
     STRICTLY require explicit `--execute`.

3. ATOMIC TRANSACTION & EXACT DATA PRESERVATION:
   - When executing, data migration runs inside a single atomic transaction.
   - Preserves exact source strings including leading/trailing whitespace.
   - Preserves exact numeric values without truncation or float rounding.
   - Converts datetimes to naive UTC datetimes matching model column types,
     preserving exact microsecond precision and UTC wall-clock values.
   - Sets PostgreSQL connection session timezone to UTC.
   - Any failure, divergence, or conflict causes an immediate ROLLBACK.

4. TRANSACTIONAL SEQUENCE SYNCHRONIZATION:
   - Uses transactional sequence restart operations (`ALTER SEQUENCE ... RESTART WITH`)
     rather than non-transactional `setval()`.
   - Sequence synchronization occurs INSIDE the data transaction BEFORE `session.commit()`.
   - Resolves `pg_get_serial_sequence()` and safely constructs quoted identifiers.
   - Any sequence failure immediately triggers a complete data rollback.
   - Data is NEVER committed before sequence synchronization succeeds.
   - Verifies next primary keys: products: 31, orders: 4, order_items: 4, admins: 2, revoked_tokens: 1.

5. NEON SSL ENFORCEMENT & CREDENTIAL REDACTION:
   - Every PostgreSQL connection enforces `sslmode=require` while preserving other query params.
   - Insecure SSL modes (`disable`, `allow`, `prefer`) are strictly rejected.
   - Connection errors and logs sanitize credentials, passwords, and connection strings.
   - SQLite test targets are unaffected by PostgreSQL SSL/options arguments.

6. STRICT IDEMPOTENCY & DIVERGENCE DETECTION:
   - If a target record exists with identical fields, it is skipped.
   - If a target record exists with divergent or conflicting fields,
     the script ABORTS and ROLLS BACK immediately.
   - Rogue target records with IDs not in source cause an immediate ABORT and ROLLBACK.
   - No target tables are ever truncated or dropped.
   - `seed_db()` is NEVER invoked.
"""

import argparse
import hashlib
import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Set up repository root in sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Import application config helpers and models
from app.config import normalize_database_url
from app.models.db import db, set_sqlite_pragma
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.admin import Admin
from app.models.revoked_token import RevokedToken
from sqlalchemy import event

# Ensure SQLite-specific foreign key PRAGMA only executes on SQLite connections
try:
    event.remove(Engine, "connect", set_sqlite_pragma)

    @event.listens_for(Engine, "connect")
    def _safe_sqlite_pragma(dbapi_connection, connection_record):
        if dbapi_connection.__class__.__module__.startswith("sqlite3"):
            cursor = dbapi_connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
except Exception:
    pass

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("migration")

# Baselines and expected counts
DEFAULT_SQLITE_PATH = BACKEND_DIR / "instance" / "store.db"
EXPECTED_SQLITE_SHA256 = "a84778d3fbe50ccb5b4427b2c413fa42010751de78b463be798a88233cafcdc6"

EXPECTED_TABLE_COUNTS = {
    "products": 30,
    "orders": 3,
    "order_items": 3,
    "admins": 1,
    "revoked_tokens": 0,
}

# (table_name, expected_last_val, expected_is_called, expected_next_id)
# With ALTER SEQUENCE ... RESTART WITH <next_id>, last_value = next_id and is_called = False
POSTGRES_SEQUENCE_SPECS = [
    ("products", 31, False, 31),
    ("orders", 4, False, 4),
    ("order_items", 4, False, 4),
    ("admins", 2, False, 2),
    ("revoked_tokens", 1, False, 1),
]

TABLE_MODELS = [
    ("products", Product),
    ("orders", Order),
    ("order_items", OrderItem),
    ("admins", Admin),
    ("revoked_tokens", RevokedToken),
]


class MigrationError(Exception):
    """Base exception for database migration errors."""
    pass


class SourceIntegrityError(MigrationError):
    """Raised when the SQLite source database fails integrity verification."""
    pass


class TargetDivergenceError(MigrationError):
    """Raised when existing target records conflict with source data."""
    pass


class SequenceSyncError(MigrationError):
    """Raised when PostgreSQL sequence synchronization fails."""
    pass


class InsecureConnectionError(MigrationError):
    """Raised when target database connection configuration is insecure."""
    pass


class TargetConnectionError(MigrationError):
    """Raised when establishing a connection to the target database fails."""
    pass


# ---------------------------------------------------------------------------
# Redaction & Sanitization Helpers
# ---------------------------------------------------------------------------

def mask_db_url(url: Optional[str]) -> str:
    """Mask credentials within database connection strings."""
    if not url:
        return "<EMPTY>"
    return re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", url)


def mask_email(email: Optional[str]) -> str:
    """Mask email addresses to protect customer privacy."""
    if not email:
        return "<EMPTY>"
    parts = email.split("@", 1)
    if len(parts) == 2:
        user, domain = parts
        masked_user = user[0] + "***" if len(user) > 0 else "***"
        return f"{masked_user}@{domain}"
    return "***"


def mask_phone(phone: Optional[str]) -> str:
    """Mask customer telephone numbers."""
    if not phone:
        return "<EMPTY>"
    return re.sub(r"\d", "*", phone[:-4]) + phone[-4:] if len(phone) >= 4 else "****"


def mask_hash(hash_val: Optional[str]) -> str:
    """Mask password hashes, revealing only cryptographic scheme and length."""
    if not hash_val:
        return "<EMPTY>"
    scheme = hash_val.split("$")[0] if "$" in hash_val else "unknown"
    return f"{scheme}:*** [length={len(hash_val)}]"


def sanitize_connection_error(exc: Exception, raw_url: Optional[str]) -> str:
    """
    Sanitize exception messages to remove sensitive credentials, passwords,
    and raw database URLs while preserving driver error details and diagnostic context.
    """
    msg = str(exc)
    if raw_url:
        masked = mask_db_url(raw_url)
        msg = msg.replace(raw_url, masked)
    msg = re.sub(r"://([^:]+):([^@]+)@", r"://\1:***@", msg)
    msg = re.sub(r"password=([^\s;]+)", r"password=***", msg)
    return msg


# ---------------------------------------------------------------------------
# Target Engine & URL Configuration (Neon SSL Enforcement)
# ---------------------------------------------------------------------------

def configure_target_url(target_url: str) -> Tuple[str, Dict[str, Any]]:
    """
    Configure and validate the target database connection parameters.
    - For PostgreSQL:
      - Normalizes scheme to postgresql+psycopg2.
      - Enforces sslmode=require if not specified.
      - Strictly rejects insecure SSL modes (disable, allow, prefer).
      - Preserves all other query parameters.
      - Returns connect_args with options='-c timezone=utc' to enforce UTC session.
    - For SQLite:
      - Preserves URL as-is without SSL/options connect_args.
    Returns (configured_url, connect_args).
    """
    clean_url = target_url.strip()
    try:
        parsed = urlparse(clean_url)
    except Exception as exc:
        raise MigrationError(f"Malformed target database URL: {exc}") from exc

    scheme_lower = (parsed.scheme or "").lower()

    # SQLite targets (used for local isolated testing)
    if scheme_lower.startswith("sqlite"):
        return clean_url, {}

    # PostgreSQL targets (Neon / Render)
    if scheme_lower in ("postgres", "postgresql", "postgresql+psycopg2"):
        query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))

        sslmode = query_params.get("sslmode", "").strip().lower()
        if sslmode:
            if sslmode in ("disable", "allow", "prefer"):
                raise InsecureConnectionError(
                    f"Insecure SSL configuration rejected: sslmode='{sslmode}' is not permitted. "
                    "Production Neon/PostgreSQL migrations strictly require sslmode='require' or stronger."
                )
            elif sslmode in ("require", "verify-ca", "verify-full"):
                pass
            else:
                raise MigrationError(f"Unrecognized or unsupported sslmode: '{sslmode}'")
        else:
            query_params["sslmode"] = "require"

        new_query = urlencode(query_params)
        reconstructed_url = parsed._replace(scheme="postgresql+psycopg2", query=new_query).geturl()
        connect_args = {
            "options": "-c timezone=utc",
            "sslmode": query_params["sslmode"],
        }
        return reconstructed_url, connect_args

    raise MigrationError(f"Unsupported database scheme: '{parsed.scheme}'")


def build_target_engine(target_url: str) -> Engine:
    """
    Build SQLAlchemy engine with sanitized error handling to prevent
    credential leakage in exception tracebacks.
    """
    configured_url, connect_args = configure_target_url(target_url)
    try:
        engine = create_engine(
            configured_url,
            future=True,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        return engine
    except Exception as exc:
        sanitized = sanitize_connection_error(exc, target_url)
        logger.error(f"Failed to create target database engine: {sanitized}")
        raise TargetConnectionError(f"Target database engine creation failed: {sanitized}") from None


# ---------------------------------------------------------------------------
# Source Verification
# ---------------------------------------------------------------------------

def compute_file_sha256(path: Path) -> str:
    """Compute SHA-256 hash of a file safely."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_sqlite_source(
    sqlite_path: Path,
    skip_hash_check: bool = False,
    skip_count_check: bool = False,
) -> Dict[str, int]:
    """
    Validate SQLite source database existence, checksum, and table record counts.
    Opens SQLite in strictly read-only mode.
    """
    if not sqlite_path.exists():
        raise SourceIntegrityError(f"SQLite source file does not exist: {sqlite_path}")

    actual_hash = compute_file_sha256(sqlite_path)
    logger.info(f"Source SQLite SHA-256: {actual_hash}")

    if not skip_hash_check:
        if actual_hash != EXPECTED_SQLITE_SHA256:
            raise SourceIntegrityError(
                f"SQLite SHA-256 mismatch! Expected {EXPECTED_SQLITE_SHA256}, got {actual_hash}."
            )
    else:
        logger.warning("SKIPPING source database SHA-256 validation as requested.")

    ro_uri = f"file:{sqlite_path.resolve().as_posix()}?mode=ro"
    logger.info(f"Opening SQLite source in read-only mode: {ro_uri}")
    conn = sqlite3.connect(ro_uri, uri=True)
    try:
        cursor = conn.cursor()
        actual_counts = {}
        for table, expected_count in EXPECTED_TABLE_COUNTS.items():
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            cnt = cursor.fetchone()[0]
            actual_counts[table] = cnt
            logger.info(f"Source table '{table}': {cnt} records (expected {expected_count})")
            if not skip_count_check and cnt != expected_count:
                raise SourceIntegrityError(
                    f"Record count mismatch in '{table}': expected {expected_count}, got {cnt}"
                )
        return actual_counts
    finally:
        conn.close()


def read_source_data(sqlite_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Read all source records from SQLite in read-only mode."""
    ro_uri = f"file:{sqlite_path.resolve().as_posix()}?mode=ro"
    conn = sqlite3.connect(ro_uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        source_data = {}
        for table_name, _ in TABLE_MODELS:
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY id ASC")
            rows = [dict(row) for row in cursor.fetchall()]
            source_data[table_name] = rows
        return source_data
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Normalization, Preparation & Exact Row Comparison
# ---------------------------------------------------------------------------

def parse_datetime(val: Any) -> Optional[datetime]:
    """
    Parse a datetime string or object into a timezone-aware UTC datetime.
    Supports ISO formats, space-separated SQLite formats, with or without fractional seconds.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, str):
        val_str = val.strip()
        try:
            dt = datetime.fromisoformat(val_str)
        except ValueError:
            dt = datetime.strptime(val_str, "%Y-%m-%d %H:%M:%S")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    raise ValueError(f"Cannot parse datetime value: {val!r}")


def to_naive_utc(val: Any) -> Optional[datetime]:
    """
    Convert datetime string or object to a timezone-naive UTC datetime.
    Preserves exact microsecond precision and UTC wall-clock values.
    Since target model columns are TIMESTAMP WITHOUT TIME ZONE, passing naive UTC
    datetimes guarantees that PostgreSQL stores the literal UTC numbers without
    session timezone conversion.
    """
    if val is None:
        return None
    dt = parse_datetime(val)
    if dt is None:
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def prepare_insert_kwargs(table_name: str, model_cls: Any, src_row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare exact model constructor kwargs from source SQLite row dictionary.
    - Preserves exact numeric values without rounding.
    - Preserves exact strings without stripping (including whitespace).
    - Converts datetimes to naive UTC datetimes matching model column types.
    """
    kwargs = {}
    datetime_fields = {
        "products": {"created_at", "updated_at"},
        "orders": {"created_at", "updated_at"},
        "admins": {"created_at", "updated_at", "last_login_at"},
        "revoked_tokens": {"revoked_at", "expires_at"},
    }

    for col in model_cls.__table__.columns:
        col_name = col.name
        if col_name not in src_row:
            continue
        val = src_row[col_name]
        if val is None:
            kwargs[col_name] = None
            continue

        if col_name in datetime_fields.get(table_name, set()):
            kwargs[col_name] = to_naive_utc(val)
        elif isinstance(col.type, db.Boolean) or col_name in ("is_active",):
            kwargs[col_name] = bool(val)
        elif isinstance(col.type, db.Integer) or col_name in ("id", "stock_quantity", "order_id", "product_id", "quantity"):
            kwargs[col_name] = int(val)
        else:
            kwargs[col_name] = val

    return kwargs


def compare_records(table: str, src: Dict[str, Any], tgt: Dict[str, Any]) -> List[str]:
    """
    Compare two record dictionaries. Returns a list of divergence descriptions,
    or an empty list if records match exactly.
    Does not round floats, does not strip strings, and checks exact datetime equality.
    """
    diffs = []
    datetime_fields = {
        "products": {"created_at", "updated_at"},
        "orders": {"created_at", "updated_at"},
        "admins": {"created_at", "updated_at", "last_login_at"},
        "revoked_tokens": {"revoked_at", "expires_at"},
    }

    for key in src.keys():
        if key not in tgt:
            continue
        src_val = src[key]
        tgt_val = tgt[key]

        if src_val is None and tgt_val is None:
            continue
        if src_val is None or tgt_val is None:
            diffs.append(f"{key}: src={src_val!r} vs tgt={tgt_val!r}")
            continue

        if key in datetime_fields.get(table, set()):
            src_dt = to_naive_utc(src_val)
            tgt_dt = to_naive_utc(tgt_val)
            if src_dt != tgt_dt:
                diffs.append(f"{key}: src={src_dt.isoformat()} vs tgt={tgt_dt.isoformat()}")
            continue

        if key in ("is_active",):
            if bool(src_val) != bool(tgt_val):
                diffs.append(f"{key}: src={bool(src_val)} vs tgt={bool(tgt_val)}")
            continue

        if key in ("id", "stock_quantity", "order_id", "product_id", "quantity"):
            if int(src_val) != int(tgt_val):
                diffs.append(f"{key}: src={int(src_val)} vs tgt={int(tgt_val)}")
            continue

        if key in ("price", "subtotal", "delivery_fee", "total_amount", "unit_price", "line_total"):
            if float(src_val) != float(tgt_val):
                diffs.append(f"{key}: src={src_val} vs tgt={tgt_val}")
            continue

        if src_val != tgt_val:
            if key == "password_hash":
                diffs.append(f"{key}: [hash mismatch]")
            elif key in ("customer_email", "customer_phone"):
                diffs.append(f"{key}: src={mask_email(str(src_val))} vs tgt={mask_email(str(tgt_val))}")
            else:
                diffs.append(f"{key}: src={src_val!r} vs tgt={tgt_val!r}")

    return diffs


# ---------------------------------------------------------------------------
# Transactional PostgreSQL Sequence Synchronization
# ---------------------------------------------------------------------------

def synchronize_postgres_sequences(conn: Any) -> List[Dict[str, Any]]:
    """
    Synchronize PostgreSQL serial/identity sequences transactionally inside the active data transaction.
    Uses:
        ALTER SEQUENCE "<schema>"."<seq_name>" RESTART WITH <next_id>;
    This DDL is fully transactional in PostgreSQL and rolls back automatically if the session transaction aborts.
    """
    if getattr(conn, "dialect", None) and conn.dialect.name != "postgresql":
        logger.info("Target dialect is not PostgreSQL; skipping sequence synchronization.")
        return []

    results = []
    logger.info("Executing transactional PostgreSQL sequence synchronization (ALTER SEQUENCE ... RESTART WITH)...")

    for table_name, exp_last_val, exp_is_called, exp_next_id in POSTGRES_SEQUENCE_SPECS:
        # 1. Resolve sequence name and validate non-NULL
        seq_name_sql = text("SELECT pg_get_serial_sequence(:tname, 'id');")
        raw_seq_name = conn.execute(seq_name_sql, {"tname": table_name}).scalar()

        if not raw_seq_name or not str(raw_seq_name).strip():
            raise SequenceSyncError(
                f"Could not resolve sequence name for table '{table_name}'. "
                f"pg_get_serial_sequence returned {raw_seq_name!r}. Sequence synchronization cannot proceed."
            )

        raw_seq_name = str(raw_seq_name).strip()

        # Parse and sanitize schema and sequence identifiers
        parts = raw_seq_name.split(".")
        if len(parts) == 2:
            schema_part, seq_part = parts
        elif len(parts) == 1:
            schema_part, seq_part = "public", parts[0]
        else:
            raise SequenceSyncError(f"Unexpected sequence identifier format: {raw_seq_name!r}")

        schema_part = schema_part.strip('"')
        seq_part = seq_part.strip('"')

        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_$]*$", schema_part) or not re.match(r"^[a-zA-Z_][a-zA-Z0-9_$]*$", seq_part):
            raise SequenceSyncError(f"Invalid characters in sequence identifier: '{schema_part}.{seq_part}'")

        safe_seq_ident = f'"{schema_part}"."{seq_part}"'

        # 2. Compute next ID from current table data
        # If table has records: next_id = MAX(id) + 1. If empty: next_id = 1.
        calc_sql = text(f'SELECT COALESCE((SELECT MAX(id) + 1 FROM "{table_name}"), 1);')
        computed_target_next_id = int(conn.execute(calc_sql).scalar())

        # 3. Transactional sequence restart: RESTART WITH <next_id>
        restart_sql = text(f"ALTER SEQUENCE {safe_seq_ident} RESTART WITH {computed_target_next_id};")
        conn.execute(restart_sql)

        # 4. Non-destructively inspect sequence state
        inspect_sql = text(f"SELECT last_value, is_called FROM {safe_seq_ident};")
        row = conn.execute(inspect_sql).fetchone()
        if not row:
            raise SequenceSyncError(f"Could not inspect sequence '{safe_seq_ident}' for table '{table_name}'.")

        last_value, is_called = row[0], bool(row[1])
        # In PostgreSQL, RESTART WITH sets last_value = next_id and is_called = False
        actual_next_id = last_value if not is_called else (last_value + 1)

        logger.info(
            f"Sequence '{safe_seq_ident}': last_value={last_value}, is_called={is_called} "
            f"-> NEXT ID will be {actual_next_id} (expected {exp_next_id})"
        )

        if actual_next_id != exp_next_id:
            raise SequenceSyncError(
                f"Sequence verification failed for '{table_name}': "
                f"expected next ID {exp_next_id}, got {actual_next_id} "
                f"(last_value={last_value}, is_called={is_called})"
            )

        results.append({
            "table": table_name,
            "sequence": safe_seq_ident,
            "last_value": last_value,
            "is_called": is_called,
            "next_id": actual_next_id,
        })

    return results


# ---------------------------------------------------------------------------
# Main Migration Execution
# ---------------------------------------------------------------------------

def run_migration(
    sqlite_path: Path,
    target_url: Optional[str] = None,
    execute: bool = False,
    skip_hash_check: bool = False,
) -> Dict[str, Any]:
    """
    Execute migration from SQLite source to target PostgreSQL database.
    Default mode is dry-run. Requires execute=True for target changes.

    CRITICAL ISOLATION & ATOMICITY GUARANTEES:
    - In dry-run mode (execute=False), NO target engine is created,
      NO connection is opened to the target, and NO DDL schema creation is performed.
    - All data insertion AND transactional sequence synchronization occur inside
      the SAME atomic transaction.
    - If sequence synchronization fails, the entire transaction rolls back cleanly.
    - Data is NEVER committed before sequence synchronization succeeds.
    """
    start_time = datetime.now(timezone.utc)
    mode_str = "EXECUTE (WRITES ENABLED)" if execute else "DRY-RUN (STRICTLY ISOLATED)"
    logger.info("=" * 60)
    logger.info(f"Starting NovaStore Migration: {mode_str}")
    logger.info(f"Target Database: {mask_db_url(target_url) if target_url else '<NONE (Isolated Dry-Run)>'}")
    logger.info("=" * 60)

    # 1. Validate SQLite Source
    source_counts = validate_sqlite_source(sqlite_path, skip_hash_check=skip_hash_check)
    source_data = read_source_data(sqlite_path)

    # 2. DRY-RUN ISOLATION BRANCH
    if not execute:
        logger.info("Dry-run mode: Source database verified successfully.")
        logger.info("Dry-run mode: Target database connection and DDL schema creation are SKIPPED.")
        planned_inserts = {tname: len(rows) for tname, rows in source_data.items()}
        for tname, cnt in planned_inserts.items():
            logger.info(f"Planned for insertion in '{tname}': {cnt} records.")

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info("=" * 60)
        logger.info(f"NovaStore Migration Finished in {elapsed:.2f}s ({mode_str})")
        logger.info("=" * 60)
        return {
            "mode": "dry-run",
            "target_connected": False,
            "source_counts": source_counts,
            "planned_insert": planned_inserts,
            "inserted": {},
            "skipped_identical": {},
            "divergences": [],
            "sequences": [],
            "duration_seconds": round(elapsed, 3),
        }

    # 3. EXECUTE BRANCH (Requires target_url)
    if not target_url:
        raise MigrationError("Target database URL is required when executing migration with --execute.")

    target_engine = build_target_engine(target_url)

    logger.info("Ensuring target schema tables exist via SQLAlchemy metadata...")
    db.metadata.create_all(bind=target_engine)

    SessionLocal = sessionmaker(bind=target_engine, autoflush=False, autocommit=False)
    session: Session = SessionLocal()

    migration_summary = {
        "mode": "execute",
        "target_connected": True,
        "source_counts": source_counts,
        "inserted": {},
        "skipped_identical": {},
        "divergences": [],
        "sequences": [],
    }

    try:
        # Process tables in foreign-key dependency order inside atomic transaction
        for table_name, model_cls in TABLE_MODELS:
            rows_to_migrate = source_data.get(table_name, [])
            logger.info(f"Processing table '{table_name}' ({len(rows_to_migrate)} source records)...")

            # Fetch existing records from target
            existing_target_objs = session.query(model_cls).order_by(model_cls.id.asc()).all()
            existing_target_map = {obj.id: obj for obj in existing_target_objs}

            # Check for rogue unexpected target records
            source_ids = {r["id"] for r in rows_to_migrate}
            rogue_target_ids = set(existing_target_map.keys()) - source_ids
            if rogue_target_ids:
                raise TargetDivergenceError(
                    f"Target table '{table_name}' contains records with IDs not in source: {sorted(rogue_target_ids)}"
                )

            inserted_count = 0
            skipped_count = 0

            for src_row in rows_to_migrate:
                record_id = src_row["id"]
                if record_id in existing_target_map:
                    tgt_obj = existing_target_map[record_id]
                    tgt_dict = {
                        col.name: getattr(tgt_obj, col.name)
                        for col in tgt_obj.__table__.columns
                    }
                    diffs = compare_records(table_name, src_row, tgt_dict)
                    if diffs:
                        err_msg = f"Divergence in '{table_name}' id={record_id}: {'; '.join(diffs)}"
                        logger.error(err_msg)
                        raise TargetDivergenceError(err_msg)
                    skipped_count += 1
                else:
                    inst_kwargs = prepare_insert_kwargs(table_name, model_cls, src_row)
                    new_obj = model_cls(**inst_kwargs)
                    session.add(new_obj)
                    inserted_count += 1

            migration_summary["inserted"][table_name] = inserted_count
            migration_summary["skipped_identical"][table_name] = skipped_count
            logger.info(
                f"Table '{table_name}': {inserted_count} inserted, "
                f"{skipped_count} identical records already present."
            )

        # 4. Explicitly flush pending inserts to target database within the active transaction
        # This ensures table records exist in the transaction before calculating MAX(id)
        logger.info("Flushing staged record insertions to database within active transaction...")
        session.flush()
        logger.info("Staged record insertions successfully flushed to database transaction.")

        # 5. Synchronize sequences INSIDE the transaction BEFORE commit (PostgreSQL only)
        if target_engine.dialect.name == "postgresql":
            seq_results = synchronize_postgres_sequences(session.connection())
            migration_summary["sequences"] = seq_results

        logger.info("Committing atomic data migration and sequence synchronization transaction...")
        session.commit()
        logger.info("Data migration and sequence synchronization transaction committed successfully.")

    except Exception as exc:
        session.rollback()
        logger.critical(f"Migration aborted due to error: {exc}")
        raise exc
    finally:
        session.close()

    target_engine.dispose()

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    migration_summary["duration_seconds"] = round(elapsed, 3)

    logger.info("=" * 60)
    logger.info(f"NovaStore Migration Finished in {elapsed:.2f}s (EXECUTE)")
    logger.info("=" * 60)
    return migration_summary


# ---------------------------------------------------------------------------
# CLI Parser
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="NovaStore SQLite to PostgreSQL Safe Migration Script",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sqlite-path",
        type=str,
        default=str(DEFAULT_SQLITE_PATH),
        help="Path to source SQLite database file",
    )
    parser.add_argument(
        "--target-url",
        type=str,
        default=None,
        help="Target database URL (defaults to DATABASE_URL environment variable)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        default=False,
        help="Execute the migration and commit changes. Default is dry-run mode.",
    )
    parser.add_argument(
        "--skip-source-hash-check",
        action="store_true",
        default=False,
        help="Skip source database SHA-256 validation (for testing fixtures only).",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    sqlite_path = Path(args.sqlite_path).resolve()
    target_url = args.target_url or os.environ.get("DATABASE_URL")

    if args.execute and not target_url:
        logger.error(
            "Target database URL is required when using --execute! "
            "Specify via --target-url or set DATABASE_URL environment variable."
        )
        sys.exit(1)

    try:
        summary = run_migration(
            sqlite_path=sqlite_path,
            target_url=target_url,
            execute=args.execute,
            skip_hash_check=args.skip_source_hash_check,
        )
        print("\nMigration Completed Successfully:")
        print(f"  Mode: {summary['mode']}")
        print(f"  Duration: {summary['duration_seconds']}s")
        if summary['mode'] == 'dry-run':
            print(f"  Target Connected: {summary['target_connected']}")
            print(f"  Planned Inserts: {summary['planned_insert']}")
        else:
            print(f"  Target Connected: {summary['target_connected']}")
            print(f"  Inserted: {summary['inserted']}")
            print(f"  Skipped (Identical): {summary['skipped_identical']}")
            if summary.get("sequences"):
                print("  Sequences:")
                for s in summary["sequences"]:
                    print(f"    - {s['table']}: sequence={s['sequence']} next_id={s['next_id']}")
    except Exception as exc:
        logger.error(f"Migration Failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
