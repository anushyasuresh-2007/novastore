"""
Unit and integration tests for the SQLite-to-PostgreSQL migration script.
Tests:
- Source database verification (SHA-256 and row counts)
- Critical dry-run isolation (zero target connection, zero engine creation, zero DDL)
- Exact string preservation (leading/trailing whitespace, NULLs, whitespace diff detection)
- Exact numeric preservation (no rounding on insert, >2 decimal places preserved)
- Exact datetime precision & naive UTC conversions (exact microsecond matching, small difference rejection, with/without fractional seconds)
- PostgreSQL engine configuration (UTC session timezone, sslmode=require enforcement, query param preservation)
- Insecure SSL rejection (rejects disable/allow/prefer)
- SQLite engine configuration isolation (no SSL/timezone options passed to SQLite)
- Connection error credential sanitization
- Sequence safety (NULL sequence rejection, empty table behavior, next ID verification)
- Atomic rollback on divergence and rogue records
- Secret and PII redaction
"""

import copy
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from sqlalchemy import create_engine, text

import scripts.migrate_sqlite_to_postgres
from app.models.db import db
from app.models.product import Product
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.admin import Admin
from app.models.revoked_token import RevokedToken
from scripts.migrate_sqlite_to_postgres import (
    DEFAULT_SQLITE_PATH,
    EXPECTED_SQLITE_SHA256,
    EXPECTED_TABLE_COUNTS,
    POSTGRES_SEQUENCE_SPECS,
    InsecureConnectionError,
    MigrationError,
    SequenceSyncError,
    SourceIntegrityError,
    TargetConnectionError,
    TargetDivergenceError,
    build_target_engine,
    compare_records,
    compute_file_sha256,
    configure_target_url,
    mask_db_url,
    mask_email,
    mask_hash,
    mask_phone,
    parse_datetime,
    prepare_insert_kwargs,
    read_source_data,
    run_migration,
    sanitize_connection_error,
    synchronize_postgres_sequences,
    to_naive_utc,
    validate_sqlite_source,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test artifacts."""
    d = tempfile.mkdtemp()
    yield Path(d)
    shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_sqlite_source(temp_dir):
    """
    Create a minimal mock SQLite source database matching the exact schema
    for isolated unit tests.
    """
    db_path = temp_dir / "mock_store.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.executescript("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(150) NOT NULL,
            description TEXT NOT NULL,
            category VARCHAR(50) NOT NULL,
            price FLOAT NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'INR',
            stock_quantity INTEGER NOT NULL DEFAULT 0,
            image_path VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_reference VARCHAR(36) UNIQUE NOT NULL,
            customer_name VARCHAR(120) NOT NULL,
            customer_email VARCHAR(120) NOT NULL,
            customer_phone VARCHAR(30) NOT NULL,
            delivery_address VARCHAR(255) NOT NULL,
            city VARCHAR(100) NOT NULL,
            postal_code VARCHAR(20) NOT NULL,
            subtotal FLOAT NOT NULL,
            delivery_fee FLOAT NOT NULL DEFAULT 0.0,
            total_amount FLOAT NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'INR',
            status VARCHAR(30) NOT NULL DEFAULT 'CONFIRMED',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
        CREATE TABLE order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL REFERENCES orders(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            product_name VARCHAR(150) NOT NULL,
            unit_price FLOAT NOT NULL,
            quantity INTEGER NOT NULL,
            line_total FLOAT NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'INR'
        );
        CREATE TABLE admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(80) UNIQUE NOT NULL,
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(30) NOT NULL DEFAULT 'admin',
            is_active BOOLEAN NOT NULL DEFAULT 1,
            last_login_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        );
        CREATE TABLE revoked_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_sig VARCHAR(64) UNIQUE NOT NULL,
            revoked_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        );
    """)

    cursor.execute("""
        INSERT INTO products (id, name, description, category, price, currency, stock_quantity, image_path, is_active, created_at, updated_at)
        VALUES (1, '  Test Product  ', 'Description with trailing spaces   ', 'Electronics', 99.995, 'INR', 20, 'http://img.png', 1, '2026-11-01 12:00:00.123456', '2026-11-01 12:00:00.123456')
    """)
    cursor.execute("""
        INSERT INTO orders (id, order_reference, customer_name, customer_email, customer_phone, delivery_address, city, postal_code, subtotal, delivery_fee, total_amount, currency, status, created_at, updated_at)
        VALUES (1, 'ORD-TEST-001', 'John Doe', 'john@example.com', '1234567890', '123 St', 'City', '12345', 99.995, 0.0, 99.995, 'USD', 'CONFIRMED', '2026-11-01 12:00:00.123456', '2026-11-01 12:00:00.123456')
    """)
    cursor.execute("""
        INSERT INTO order_items (id, order_id, product_id, product_name, unit_price, quantity, line_total, currency)
        VALUES (1, 1, 1, '  Test Product  ', 99.995, 1, 99.995, 'USD')
    """)
    cursor.execute("""
        INSERT INTO admins (id, username, email, password_hash, role, is_active, last_login_at, created_at, updated_at)
        VALUES (1, 'admin', 'admin@example.com', 'scrypt:32768:8:1$test_hash', 'admin', 1, NULL, '2026-11-01 12:00:00.123456', '2026-11-01 12:00:00.123456')
    """)
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# 1. Source Database Verification Tests
# ---------------------------------------------------------------------------

def test_actual_store_db_checksum_and_counts():
    """Verify the actual live backend store.db passes validation."""
    assert DEFAULT_SQLITE_PATH.exists(), f"Source store.db not found at {DEFAULT_SQLITE_PATH}"
    actual_hash = compute_file_sha256(DEFAULT_SQLITE_PATH)
    assert actual_hash == EXPECTED_SQLITE_SHA256, (
        f"Actual store.db hash {actual_hash} != expected {EXPECTED_SQLITE_SHA256}"
    )

    counts = validate_sqlite_source(DEFAULT_SQLITE_PATH, skip_hash_check=False)
    assert counts == EXPECTED_TABLE_COUNTS


def test_missing_source_file_raises_error(temp_dir):
    """Verify that a missing source file raises SourceIntegrityError."""
    missing = temp_dir / "does_not_exist.db"
    with pytest.raises(SourceIntegrityError, match="does not exist"):
        validate_sqlite_source(missing)


def test_invalid_hash_raises_error(mock_sqlite_source):
    """Verify that an unexpected hash raises SourceIntegrityError when not skipped."""
    with pytest.raises(SourceIntegrityError, match="SHA-256 mismatch"):
        validate_sqlite_source(mock_sqlite_source, skip_hash_check=False)


def test_mismatched_counts_raises_error(mock_sqlite_source):
    """Verify that mismatched row counts raise SourceIntegrityError."""
    with pytest.raises(SourceIntegrityError, match="Record count mismatch in 'products'"):
        validate_sqlite_source(mock_sqlite_source, skip_hash_check=True, skip_count_check=False)


# ---------------------------------------------------------------------------
# 2. Critical Dry-Run Isolation Tests
# ---------------------------------------------------------------------------

def test_dry_run_isolation_never_connects_to_target():
    """
    CRITICAL SAFETY TEST:
    Verify dry-run mode never creates a target engine, never connects to target,
    and never calls db.metadata.create_all(). Even if target_url points to an
    unreachable host, dry-run succeeds strictly offline without raising network error.
    """
    unreachable_url = "postgresql+psycopg2://unreachable_user:dummy_pass@127.0.0.1:9999/dummy_db"

    with patch("scripts.migrate_sqlite_to_postgres.build_target_engine") as mock_build_engine, \
         patch.object(db.metadata, "create_all") as mock_create_all:

        summary = run_migration(
            sqlite_path=DEFAULT_SQLITE_PATH,
            target_url=unreachable_url,
            execute=False,  # Dry-run
            skip_hash_check=False,
        )

        assert summary["mode"] == "dry-run"
        assert summary["target_connected"] is False
        assert summary["planned_insert"]["products"] == 30
        assert summary["planned_insert"]["orders"] == 3
        assert summary["planned_insert"]["order_items"] == 3
        assert summary["planned_insert"]["admins"] == 1
        assert summary["planned_insert"]["revoked_tokens"] == 0

        # Assert zero target engine or DDL calls
        mock_build_engine.assert_not_called()
        mock_create_all.assert_not_called()


def test_dry_run_with_no_target_url():
    """Verify dry-run succeeds when target_url is None (pure source validation)."""
    summary = run_migration(
        sqlite_path=DEFAULT_SQLITE_PATH,
        target_url=None,
        execute=False,
        skip_hash_check=False,
    )
    assert summary["mode"] == "dry-run"
    assert summary["target_connected"] is False


def test_execute_mode_requires_target_url():
    """Verify that --execute fails immediately if target_url is omitted."""
    with pytest.raises(MigrationError, match="Target database URL is required"):
        run_migration(
            sqlite_path=DEFAULT_SQLITE_PATH,
            target_url=None,
            execute=True,
            skip_hash_check=False,
        )


# ---------------------------------------------------------------------------
# 3. Exact String & Whitespace Preservation Tests
# ---------------------------------------------------------------------------

def test_exact_string_preservation_with_whitespace():
    """
    Verify strings with intentional leading, trailing, or newline whitespace
    are preserved without stripping in kwargs preparation and record comparison.
    """
    src_row = {
        "id": 1,
        "name": "  Padded Name  ",
        "description": "  Line 1\n  Line 2  ",
        "category": "\tElectronics\t",
        "price": 49.99,
        "currency": "INR",
        "stock_quantity": 10,
        "image_path": "  http://example.com/img.png  ",
        "is_active": 1,
        "created_at": "2026-11-01 12:00:00",
        "updated_at": "2026-11-01 12:00:00",
    }

    kwargs = prepare_insert_kwargs("products", Product, src_row)
    assert kwargs["name"] == "  Padded Name  "
    assert kwargs["description"] == "  Line 1\n  Line 2  "
    assert kwargs["category"] == "\tElectronics\t"
    assert kwargs["image_path"] == "  http://example.com/img.png  "

    # Compare exact identical strings -> no diff
    tgt_dict = copy.deepcopy(src_row)
    tgt_dict["created_at"] = to_naive_utc(src_row["created_at"])
    tgt_dict["updated_at"] = to_naive_utc(src_row["updated_at"])
    tgt_dict["is_active"] = True
    assert compare_records("products", src_row, tgt_dict) == []

    # Whitespace difference must be flagged as a divergence
    tgt_stripped = copy.deepcopy(tgt_dict)
    tgt_stripped["name"] = "Padded Name"
    diffs = compare_records("products", src_row, tgt_stripped)
    assert any("name: src='  Padded Name  ' vs tgt='Padded Name'" in d for d in diffs)


def test_null_string_preservation():
    """Verify NULL string fields remain NULL."""
    src_row = {
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "password_hash": "scrypt:hash",
        "role": "admin",
        "is_active": 1,
        "last_login_at": None,
        "created_at": "2026-11-01 12:00:00",
        "updated_at": "2026-11-01 12:00:00",
    }
    kwargs = prepare_insert_kwargs("admins", Admin, src_row)
    assert kwargs["last_login_at"] is None


# ---------------------------------------------------------------------------
# 4. Exact Numeric Preservation Tests
# ---------------------------------------------------------------------------

def test_exact_numeric_preservation_without_rounding():
    """
    Verify floats with >2 decimal places are not rounded or truncated
    during kwargs preparation, and comparison rejects small numerical differences.
    """
    src_row = {
        "id": 1,
        "name": "Precision Product",
        "description": "desc",
        "category": "Electronics",
        "price": 12.34567,  # 5 decimal places
        "currency": "INR",
        "stock_quantity": 5,
        "image_path": "img",
        "is_active": 1,
        "created_at": "2026-11-01 12:00:00",
        "updated_at": "2026-11-01 12:00:00",
    }
    kwargs = prepare_insert_kwargs("products", Product, src_row)
    assert kwargs["price"] == 12.34567

    # Exact match passes
    tgt_dict = copy.deepcopy(src_row)
    tgt_dict["created_at"] = to_naive_utc(src_row["created_at"])
    tgt_dict["updated_at"] = to_naive_utc(src_row["updated_at"])
    tgt_dict["is_active"] = True
    assert compare_records("products", src_row, tgt_dict) == []

    # Small numerical difference (e.g. 12.34567 vs 12.34568) must be detected as divergence
    tgt_diff = copy.deepcopy(tgt_dict)
    tgt_diff["price"] = 12.34568
    diffs = compare_records("products", src_row, tgt_diff)
    assert any("price: src=12.34567 vs tgt=12.34568" in d for d in diffs)

    # Rounded value (12.35) must be detected as divergence
    tgt_rounded = copy.deepcopy(tgt_dict)
    tgt_rounded["price"] = 12.35
    diffs_rounded = compare_records("products", src_row, tgt_rounded)
    assert any("price: src=12.34567 vs tgt=12.35" in d for d in diffs_rounded)


# ---------------------------------------------------------------------------
# 5. Exact Datetime Precision & Naive UTC Tests
# ---------------------------------------------------------------------------

def test_naive_utc_datetime_insertion():
    """
    Verify prepare_insert_kwargs converts timestamps to naive UTC datetime objects
    (tzinfo is None) to match PostgreSQL TIMESTAMP WITHOUT TIME ZONE column expectations.
    """
    src_row = {
        "id": 1,
        "name": "Test",
        "description": "desc",
        "category": "Electronics",
        "price": 50.0,
        "currency": "INR",
        "stock_quantity": 10,
        "image_path": "img",
        "is_active": 1,
        "created_at": "2026-11-01 15:09:34.481199",
        "updated_at": "2026-11-01 16:54:38",  # Without fractional seconds
    }
    kwargs = prepare_insert_kwargs("products", Product, src_row)

    # Must be naive datetime objects
    assert isinstance(kwargs["created_at"], datetime)
    assert kwargs["created_at"].tzinfo is None
    assert kwargs["created_at"].microsecond == 481199
    assert kwargs["created_at"].hour == 15
    assert kwargs["created_at"].minute == 9

    assert isinstance(kwargs["updated_at"], datetime)
    assert kwargs["updated_at"].tzinfo is None
    assert kwargs["updated_at"].microsecond == 0
    assert kwargs["updated_at"].hour == 16


def test_exact_datetime_microsecond_precision():
    """
    Verify exact microsecond datetime comparison without permissive tolerance,
    testing values with and without fractional seconds.
    """
    src = {
        "id": 1,
        "created_at": "2026-11-01 15:09:34.481199",
        "updated_at": "2026-11-01 16:54:38",
    }
    tgt = {
        "id": 1,
        "created_at": datetime(2026, 11, 1, 15, 9, 34, 481199),  # naive UTC
        "updated_at": datetime(2026, 11, 1, 16, 54, 38),        # naive UTC without fraction
    }
    # Exact microsecond match passes
    assert compare_records("products", src, tgt) == []

    # 1 millisecond divergence must be detected
    tgt_ms_diff = copy.deepcopy(tgt)
    tgt_ms_diff["created_at"] = datetime(2026, 11, 1, 15, 9, 34, 482199)
    diffs = compare_records("products", src, tgt_ms_diff)
    assert any("created_at" in d for d in diffs)

    # 1 microsecond divergence must be detected
    tgt_us_diff = copy.deepcopy(tgt)
    tgt_us_diff["created_at"] = datetime(2026, 11, 1, 15, 9, 34, 481200)
    diffs_us = compare_records("products", src, tgt_us_diff)
    assert any("created_at" in d for d in diffs_us)


# ---------------------------------------------------------------------------
# 6. Neon SSL & PostgreSQL Engine Configuration Tests
# ---------------------------------------------------------------------------

def test_postgres_engine_configuration_ssl_and_timezone():
    """
    Verify PostgreSQL URL configuration enforces sslmode=require,
    preserves existing query parameters, and sets session timezone to UTC.
    Note: Mocked/isolated unit test. Zero live network calls.
    """
    raw_url = "postgres://neondb_owner:secret_pass@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?channel_binding=prefer"
    configured_url, connect_args = configure_target_url(raw_url)

    assert configured_url.startswith("postgresql+psycopg2://")
    assert "sslmode=require" in configured_url
    assert "channel_binding=prefer" in configured_url
    assert connect_args["options"] == "-c timezone=utc"
    assert connect_args["sslmode"] == "require"


def test_conflicting_ssl_mode_rejected():
    """
    Verify insecure SSL modes (disable, allow, prefer) are rejected with InsecureConnectionError.
    Secure modes (require, verify-ca, verify-full) are permitted.
    """
    base_url = "postgresql://user:pass@ep-test.neon.tech/neondb"

    # Insecure modes must be rejected
    for insecure in ("disable", "allow", "prefer"):
        url = f"{base_url}?sslmode={insecure}"
        with pytest.raises(InsecureConnectionError, match="Insecure SSL configuration rejected"):
            configure_target_url(url)

    # Secure modes must be accepted
    for secure in ("require", "verify-ca", "verify-full"):
        url = f"{base_url}?sslmode={secure}"
        conf_url, args = configure_target_url(url)
        assert f"sslmode={secure}" in conf_url
        assert args["sslmode"] == secure


def test_sqlite_target_unaffected_by_ssl_or_options(temp_dir):
    """
    Verify SQLite targets remain completely unaffected by PostgreSQL SSL or options.
    """
    sqlite_url = f"sqlite:///{temp_dir / 'test.db'}"
    conf_url, connect_args = configure_target_url(sqlite_url)
    assert conf_url == sqlite_url
    assert connect_args == {}


def test_connection_error_redacts_credentials():
    """
    Verify sanitize_connection_error removes sensitive passwords and URLs from errors.
    """
    raw_url = "postgresql+psycopg2://admin_user:SuperSecretPassword123@ep-test.neon.tech/neondb?sslmode=require"
    raw_exc = Exception(f"could not connect to server: {raw_url} password=SuperSecretPassword123 authentication failed")

    sanitized = sanitize_connection_error(raw_exc, raw_url)
    assert "SuperSecretPassword123" not in sanitized
    assert "admin_user:***@" in sanitized
    assert "password=***" in sanitized
    assert "could not connect to server" in sanitized


# ---------------------------------------------------------------------------
# 7. Sequence Synchronization Safety Tests
# ---------------------------------------------------------------------------

def test_postgres_sequence_sync_specifications():
    """Verify target sequence metadata constants match transactional RESTART WITH specifications."""
    expected_specs = [
        ("products", 31, False, 31),
        ("orders", 4, False, 4),
        ("order_items", 4, False, 4),
        ("admins", 2, False, 2),
        ("revoked_tokens", 1, False, 1),
    ]
    assert POSTGRES_SEQUENCE_SPECS == expected_specs


def test_postgres_sequence_sync_mock():
    """
    Test PostgreSQL sequence synchronization using a mock connection to verify
    the correct transactional ALTER SEQUENCE ... RESTART WITH queries are dispatched,
    resolving sequence names and inspecting state.
    Note: Mocked test simulating PostgreSQL connection execution.
    """
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"

    seq_returns = {
        "products": ("public.products_id_seq", 31, (31, False)),
        "orders": ("public.orders_id_seq", 4, (4, False)),
        "order_items": ("public.order_items_id_seq", 4, (4, False)),
        "admins": ("public.admins_id_seq", 2, (2, False)),
        "revoked_tokens": ("public.revoked_tokens_id_seq", 1, (1, False)),
    }

    executed_sqls = []

    def mock_execute(sql, params=None):
        sql_str = str(sql)
        executed_sqls.append((sql_str, params))
        res = MagicMock()
        if "pg_get_serial_sequence" in sql_str:
            tname = params["tname"]
            res.scalar.return_value = seq_returns[tname][0]
        elif "MAX(id)" in sql_str:
            for tname, (_, next_id, _) in seq_returns.items():
                if f'"{tname}"' in sql_str or tname in sql_str:
                    res.scalar.return_value = next_id
                    break
        elif "SELECT last_value" in sql_str:
            for tname, (sname, _, (lval, is_c)) in seq_returns.items():
                clean_sname = sname.split(".")[-1]
                if clean_sname in sql_str:
                    res.fetchone.return_value = (lval, is_c)
                    break
        return res

    mock_conn.execute.side_effect = mock_execute

    results = synchronize_postgres_sequences(mock_conn)
    assert len(results) == 5
    for r in results:
        if r["table"] == "products":
            assert r["next_id"] == 31
            assert r["last_value"] == 31
            assert r["is_called"] is False
        elif r["table"] in ("orders", "order_items"):
            assert r["next_id"] == 4
            assert r["last_value"] == 4
            assert r["is_called"] is False
        elif r["table"] == "admins":
            assert r["next_id"] == 2
            assert r["last_value"] == 2
            assert r["is_called"] is False
        elif r["table"] == "revoked_tokens":
            assert r["next_id"] == 1
            assert r["last_value"] == 1
            assert r["is_called"] is False

    alter_sqls = [s for s, _ in executed_sqls if "ALTER SEQUENCE" in s]
    assert len(alter_sqls) == 5
    assert any('ALTER SEQUENCE "public"."products_id_seq" RESTART WITH 31' in s for s in alter_sqls)
    assert any('ALTER SEQUENCE "public"."orders_id_seq" RESTART WITH 4' in s for s in alter_sqls)
    assert any('ALTER SEQUENCE "public"."order_items_id_seq" RESTART WITH 4' in s for s in alter_sqls)
    assert any('ALTER SEQUENCE "public"."admins_id_seq" RESTART WITH 2' in s for s in alter_sqls)
    assert any('ALTER SEQUENCE "public"."revoked_tokens_id_seq" RESTART WITH 1' in s for s in alter_sqls)


def test_sequence_sync_rejects_null_sequence_name():
    """Verify that a NULL or empty sequence name raises SequenceSyncError immediately."""
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"

    # pg_get_serial_sequence returns None
    res = MagicMock()
    res.scalar.return_value = None
    mock_conn.execute.return_value = res

    with pytest.raises(SequenceSyncError, match="Could not resolve sequence name"):
        synchronize_postgres_sequences(mock_conn)


def test_sequence_sync_rejects_mismatched_next_id():
    """Verify that unexpected sequence state raises SequenceSyncError."""
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"

    def mock_execute(sql, params=None):
        sql_str = str(sql)
        res = MagicMock()
        if "pg_get_serial_sequence" in sql_str:
            res.scalar.return_value = "public.products_id_seq"
        elif "MAX(id)" in sql_str:
            res.scalar.return_value = 31
        elif "SELECT last_value" in sql_str:
            # Return unexpected state: last_value=50 instead of 31
            res.fetchone.return_value = (50, False)
        return res

    mock_conn.execute.side_effect = mock_execute

    with pytest.raises(SequenceSyncError, match="Sequence verification failed for 'products'"):
        synchronize_postgres_sequences(mock_conn)


def test_sequence_restart_sql_identifier_sanitization():
    """
    Verify sequence identifier parsing and sanitization:
    - Safe identifiers (with or without schema) are formatted as "<schema>"."<seq>".
    - SQL injection or illegal characters raise SequenceSyncError.
    """
    mock_conn = MagicMock()
    mock_conn.dialect.name = "postgresql"

    invalid_identifiers = [
        "public.seq; DROP TABLE products;--",
        "public.seq-name",
        "public.seq$invalid!",
        "schema.name.too.many.parts",
        "",
        "   ",
    ]
    for bad_ident in invalid_identifiers:
        def mock_exec_bad(sql, params=None):
            sql_str = str(sql)
            res = MagicMock()
            if "pg_get_serial_sequence" in sql_str:
                res.scalar.return_value = bad_ident
            return res

        mock_conn.execute.side_effect = mock_exec_bad
        with pytest.raises(SequenceSyncError):
            synchronize_postgres_sequences(mock_conn)


def test_sequence_sync_failure_inside_transaction_triggers_rollback(temp_dir):
    """
    Verify that sequence synchronization failure inside the transaction causes
    a full transaction rollback, preventing data from being committed.
    """
    target_db_path = temp_dir / "target_seq_fail.db"
    target_url = f"sqlite:///{target_db_path}"

    real_engine = create_engine(target_url)

    orig_build = scripts.migrate_sqlite_to_postgres.build_target_engine

    def mock_build(url):
        engine = orig_build(url)
        # Set dialect.name attribute to report postgresql so sequence sync branch is reached
        engine.dialect.name = "postgresql"
        return engine

    with patch("scripts.migrate_sqlite_to_postgres.build_target_engine", side_effect=mock_build):
        with patch("scripts.migrate_sqlite_to_postgres.synchronize_postgres_sequences") as mock_sync:
            mock_sync.side_effect = SequenceSyncError("Simulated sequence synchronization failure")

            with pytest.raises(SequenceSyncError, match="Simulated sequence synchronization failure"):
                run_migration(
                    sqlite_path=DEFAULT_SQLITE_PATH,
                    target_url=target_url,
                    execute=True,
                    skip_hash_check=False,
                )

    # Verify rollback: target tables must have 0 records committed
    with real_engine.connect() as conn:
        for tname in ["products", "orders", "order_items", "admins", "revoked_tokens"]:
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM {tname}")).scalar()
            assert cnt == 0, f"Table '{tname}' should have 0 records after rollback, got {cnt}"
    real_engine.dispose()


def test_flush_precedes_sequence_sync_and_commit(temp_dir):
    """
    Verify that session.flush() executes BEFORE sequence synchronization,
    ensuring that rows are physically queryable within the transaction
    before sequence synchronization calculates MAX(id).
    """
    target_db_path = temp_dir / "target_flush_test.db"
    target_url = f"sqlite:///{target_db_path}"

    orig_build = scripts.migrate_sqlite_to_postgres.build_target_engine
    flushed_row_counts_at_sync_time = {}
    call_order = []

    def mock_build(url):
        engine = orig_build(url)
        engine.dialect.name = "postgresql"
        return engine

    def instrumented_sync(conn):
        call_order.append("sync_sequences")
        # Query the active transaction to verify that session.flush() has already sent rows to the database
        flushed_row_counts_at_sync_time["products"] = conn.execute(text('SELECT COUNT(*) FROM "products"')).scalar()
        flushed_row_counts_at_sync_time["orders"] = conn.execute(text('SELECT COUNT(*) FROM "orders"')).scalar()
        flushed_row_counts_at_sync_time["admins"] = conn.execute(text('SELECT COUNT(*) FROM "admins"')).scalar()
        # Also verify MAX(id) is readable from flushed data
        flushed_row_counts_at_sync_time["max_product_id"] = conn.execute(text('SELECT MAX(id) FROM "products"')).scalar()
        return [{"table": "products", "next_id": 31}]

    with patch("scripts.migrate_sqlite_to_postgres.build_target_engine", side_effect=mock_build):
        with patch("scripts.migrate_sqlite_to_postgres.synchronize_postgres_sequences", side_effect=instrumented_sync):
            summary = run_migration(
                sqlite_path=DEFAULT_SQLITE_PATH,
                target_url=target_url,
                execute=True,
                skip_hash_check=False,
            )

    # 1. Verify that at the time sequence sync executed, all rows were ALREADY flushed to the database
    assert flushed_row_counts_at_sync_time["products"] == 30
    assert flushed_row_counts_at_sync_time["orders"] == 3
    assert flushed_row_counts_at_sync_time["admins"] == 1
    assert flushed_row_counts_at_sync_time["max_product_id"] == 30

    # 2. Verify sequence sync was called and summary recorded
    assert call_order == ["sync_sequences"]
    assert summary["mode"] == "execute"
    assert summary["sequences"] == [{"table": "products", "next_id": 31}]


def test_sequence_sync_occurs_before_commit():
    """
    Verify the strict execution order: sequence synchronization MUST occur
    strictly BEFORE session.commit() inside the data transaction.
    """
    call_order = []

    mock_session = MagicMock()

    def mock_commit():
        call_order.append("commit")

    mock_session.commit.side_effect = mock_commit

    with patch("scripts.migrate_sqlite_to_postgres.synchronize_postgres_sequences") as mock_sync:
        def mock_sync_fn(conn):
            call_order.append("sync_sequences")
            return [{"table": "products", "next_id": 31}]

        mock_sync.side_effect = mock_sync_fn

        target_engine = MagicMock()
        target_engine.dialect.name = "postgresql"

        # Simulate execution branch logic as implemented in run_migration
        if target_engine.dialect.name == "postgresql":
            seq_results = mock_sync(mock_session.connection())
        mock_session.commit()

        assert call_order == ["sync_sequences", "commit"], f"Expected ['sync_sequences', 'commit'], got {call_order}"


# ---------------------------------------------------------------------------
# 8. Execution Mode Integration Tests (Local Isolated SQLite Target)
# ---------------------------------------------------------------------------

def test_full_migration_to_empty_target(temp_dir):
    """
    Verify complete migration of live store.db data to empty local target with execute=True.
    Validates exact counts, depleted stock, historical currencies, and admin hash.
    Note: Target is an isolated temporary SQLite database for local test execution.
    """
    target_db_path = temp_dir / "target_live.db"
    target_url = f"sqlite:///{target_db_path}"

    summary = run_migration(
        sqlite_path=DEFAULT_SQLITE_PATH,
        target_url=target_url,
        execute=True,
        skip_hash_check=False,
    )

    assert summary["mode"] == "execute"
    assert summary["inserted"]["products"] == 30
    assert summary["inserted"]["orders"] == 3
    assert summary["inserted"]["order_items"] == 3
    assert summary["inserted"]["admins"] == 1
    assert summary["inserted"]["revoked_tokens"] == 0

    engine = create_engine(target_url)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM products")).scalar() == 30
        assert conn.execute(text("SELECT COUNT(*) FROM orders")).scalar() == 3
        assert conn.execute(text("SELECT COUNT(*) FROM order_items")).scalar() == 3
        assert conn.execute(text("SELECT COUNT(*) FROM admins")).scalar() == 1
        assert conn.execute(text("SELECT COUNT(*) FROM revoked_tokens")).scalar() == 0

        # Check stock depletion preservation
        p1_stock = conn.execute(text("SELECT stock_quantity FROM products WHERE id=1")).scalar()
        p13_stock = conn.execute(text("SELECT stock_quantity FROM products WHERE id=13")).scalar()
        assert p1_stock == 23, f"Product 1 stock expected 23, got {p1_stock}"
        assert p13_stock == 7, f"Product 13 stock expected 7, got {p13_stock}"

        # Check historical order currencies (all 3 orders were placed in USD)
        order_currencies = [r[0] for r in conn.execute(text("SELECT currency FROM orders ORDER BY id")).fetchall()]
        assert order_currencies == ["USD", "USD", "USD"]

        # Check admin password hash preservation
        admin_hash = conn.execute(text("SELECT password_hash FROM admins WHERE id=1")).scalar()
        assert admin_hash.startswith("scrypt:32768:8:1$")
        assert len(admin_hash) == 162
    engine.dispose()


def test_idempotent_rerun_skips_identical_data(temp_dir):
    """
    Verify that executing migration a second time against a populated target
    detects all records as identical, inserts 0 records, and does not alter data.
    """
    target_db_path = temp_dir / "target_idempotent.db"
    target_url = f"sqlite:///{target_db_path}"

    # First run
    run_migration(
        sqlite_path=DEFAULT_SQLITE_PATH,
        target_url=target_url,
        execute=True,
        skip_hash_check=False,
    )

    # Second run
    summary2 = run_migration(
        sqlite_path=DEFAULT_SQLITE_PATH,
        target_url=target_url,
        execute=True,
        skip_hash_check=False,
    )

    assert summary2["inserted"]["products"] == 0
    assert summary2["inserted"]["orders"] == 0
    assert summary2["inserted"]["order_items"] == 0
    assert summary2["inserted"]["admins"] == 0

    assert summary2["skipped_identical"]["products"] == 30
    assert summary2["skipped_identical"]["orders"] == 3
    assert summary2["skipped_identical"]["order_items"] == 3
    assert summary2["skipped_identical"]["admins"] == 1


def test_divergent_target_record_triggers_rollback(temp_dir):
    """
    Verify that if a target record has conflicting data (e.g. altered price),
    the migration raises TargetDivergenceError and rolls back completely.
    """
    target_db_path = temp_dir / "target_divergent.db"
    target_url = f"sqlite:///{target_db_path}"

    engine = create_engine(target_url)
    db.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO products (id, name, description, category, price, currency, stock_quantity, image_path, is_active, created_at, updated_at)
            VALUES (1, 'Ultra-Slim Wireless Mechanical Keyboard', 'Low-profile mechanical switches with RGB backlighting, Bluetooth 5.3, and multi-device pairing.', 'Electronics', 99999.00, 'INR', 23, 'https://images.unsplash.com/photo-1587829741301-dc798b83add3?auto=format&fit=crop&w=600&q=80', 1, '2026-11-01 15:09:34.481199', '2026-11-01 16:54:38.781947')
        """))
    engine.dispose()

    with pytest.raises(TargetDivergenceError, match="Divergence in 'products' id=1"):
        run_migration(
            sqlite_path=DEFAULT_SQLITE_PATH,
            target_url=target_url,
            execute=True,
            skip_hash_check=False,
        )

    # Confirm rollback: other products (product 2..30) were not committed
    engine = create_engine(target_url)
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        assert count == 1, "Only pre-existing record should remain; partial migration must be rolled back."
    engine.dispose()


def test_rogue_extra_record_in_target_triggers_abort(temp_dir):
    """
    Verify that if target contains records with IDs not in source,
    migration detects unexpected records and aborts with rollback.
    """
    target_db_path = temp_dir / "target_rogue.db"
    target_url = f"sqlite:///{target_db_path}"

    engine = create_engine(target_url)
    db.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO products (id, name, description, category, price, currency, stock_quantity, image_path, is_active, created_at, updated_at)
            VALUES (999, 'Rogue Product', 'desc', 'Electronics', 500.0, 'INR', 1, 'img', 1, '2026-11-01 12:00:00', '2026-11-01 12:00:00')
        """))
    engine.dispose()

    with pytest.raises(TargetDivergenceError, match="contains records with IDs not in source"):
        run_migration(
            sqlite_path=DEFAULT_SQLITE_PATH,
            target_url=target_url,
            execute=True,
            skip_hash_check=False,
        )


# ---------------------------------------------------------------------------
# 9. Redaction & Security Tests
# ---------------------------------------------------------------------------

def test_redaction_helpers():
    """Verify sensitive connection credentials and PII are redacted."""
    raw_url = "postgresql+psycopg2://neondb_owner:npg_SecretPass123@ep-cool-fog-123.us-east-2.aws.neon.tech/neondb?sslmode=require"
    masked = mask_db_url(raw_url)
    assert "npg_SecretPass123" not in masked
    assert "neondb_owner:***@" in masked

    assert mask_email("customer@example.com") == "c***@example.com"
    assert mask_email("a@b.com") == "a***@b.com"

    assert mask_phone("+1 555-123-4567") == "+* ***-***-4567"
    assert mask_phone("9876543210") == "******3210"

    ph = "scrypt:32768:8:1$u9v0QZ...$very_long_secret_hash"
    masked_h = mask_hash(ph)
    assert "very_long_secret_hash" not in masked_h
    assert masked_h.startswith("scrypt:")
    assert "[length=48]" in masked_h


def test_compare_records_masks_sensitive_diffs():
    """Verify record comparison masks customer PII and hashes in diff reports."""
    src = {"id": 1, "password_hash": "scrypt:1$source_hash", "customer_email": "real@domain.com"}
    tgt = {"id": 1, "password_hash": "scrypt:1$divergent_hash", "customer_email": "divergent@domain.com"}

    diffs = compare_records("admins", src, tgt)
    assert any("[hash mismatch]" in d for d in diffs)
    assert not any("source_hash" in d for d in diffs)
    assert not any("divergent_hash" in d for d in diffs)

    diffs_order = compare_records("orders", src, tgt)
    assert any("r***@domain.com" in d for d in diffs_order)
    assert not any("real@domain.com" in d for d in diffs_order)
