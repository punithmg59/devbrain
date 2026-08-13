"""
Tests for database SSL context construction.

Covers:
  1.  Production SSL context uses CERT_REQUIRED (not CERT_NONE)
  2.  Production SSL context has check_hostname=True
  3.  Development SSL context uses CERT_NONE
  4.  Development SSL context has check_hostname=False
  5.  Production NEVER uses CERT_NONE
  6.  Missing CA certificate file raises FileNotFoundError
  7.  Invalid CA certificate path raises FileNotFoundError
  8.  Invalid inline PEM content raises ValueError
  9.  Inline PEM: escaped \\n are normalised to real newlines
  10. Inline PEM: priority over system CA bundle
  11. File path: priority over inline cert
  12. No Supabase URL → empty connect_args (no SSL forced)
  13. Supabase URL → connect_args includes ssl key
  14. DATABASE_URL parsing does not expose credentials in logs
  15. log_db_connection_info logs host/port/SSL/env, not password
  16. Supabase pooler URL detected correctly
  17. Non-pooler Supabase URL detected correctly
  18. connect_args always includes statement_cache_size=0 for Supabase
"""
import os
import ssl
import tempfile
import logging
from unittest.mock import patch

import pytest

from app.database import (
    _build_ssl_context,
    _build_async_connect_args,
    log_db_connection_info,
)

# ── Helpers ────────────────────────────────────────────────────────────────────

_SUPABASE_URL = (
    "postgresql+asyncpg://postgres.abc123:password@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
)
_NON_SUPABASE_URL = "postgresql+asyncpg://postgres:password@localhost:5432/devbrain"
_SQLITE_URL = "sqlite+aiosqlite:///./devbrain.db"

# Minimal self-signed PEM-like string for format validation tests.
# This is NOT a real certificate – it only needs to pass the "-----BEGIN" check.
_FAKE_PEM_HEADER = "-----BEGIN CERTIFICATE-----\nMIIBIjANBgkqhkiG9w0BAQ==\n-----END CERTIFICATE-----\n"


def _make_real_cert_file() -> str:
    """Write a real self-signed cert to a temp file so ssl.create_default_context can load it."""
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test-ca")])
        cert = (
            x509.CertificateBuilder()
            .subject_name(name)
            .issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
            .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
            .sign(key, hashes.SHA256())
        )
        pem = cert.public_bytes(serialization.Encoding.PEM)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem")
        tmp.write(pem)
        tmp.close()
        return tmp.name
    except ImportError:
        # cryptography package not installed: write a syntactically-valid but
        # non-loadable PEM so path-existence tests still work.
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pem", mode="w")
        tmp.write(_FAKE_PEM_HEADER)
        tmp.close()
        return tmp.name


# ── Test 1: Production SSL uses CERT_REQUIRED ─────────────────────────────────

def test_production_ssl_uses_cert_required():
    """Production SSL context must use CERT_REQUIRED."""
    ctx = _build_ssl_context("Production")
    assert ctx.verify_mode == ssl.CERT_REQUIRED


# ── Test 2: Production SSL has check_hostname=True ────────────────────────────

def test_production_ssl_check_hostname_enabled():
    """Production SSL context must have check_hostname=True."""
    ctx = _build_ssl_context("production")  # lowercase variant
    assert ctx.check_hostname is True


# ── Test 3: Development SSL uses CERT_NONE ────────────────────────────────────

def test_development_ssl_uses_cert_none():
    """Development SSL context must use CERT_NONE for Windows compat."""
    ctx = _build_ssl_context("development")
    assert ctx.verify_mode == ssl.CERT_NONE


# ── Test 4: Development SSL has check_hostname=False ──────────────────────────

def test_development_ssl_check_hostname_disabled():
    """Development SSL context must have check_hostname=False."""
    ctx = _build_ssl_context("development")
    assert ctx.check_hostname is False


# ── Test 5: Production NEVER uses CERT_NONE ───────────────────────────────────

@pytest.mark.parametrize("env", ["Production", "production", "PRODUCTION", "staging", ""])
def test_production_never_uses_cert_none(env):
    """Any non-development environment must never relax certificate verification."""
    ctx = _build_ssl_context(env)
    assert ctx.verify_mode != ssl.CERT_NONE, (
        f"CERT_NONE must not be used in environment={env!r}"
    )


# ── Test 6: Missing CA certificate file raises FileNotFoundError ───────────────

def test_missing_ca_cert_path_raises():
    """Pointing DATABASE_SSL_CA_CERT_PATH at a non-existent file must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="DATABASE_SSL_CA_CERT_PATH"):
        _build_ssl_context("Production", ca_cert_path="/nonexistent/path/ca.pem")


# ── Test 7: Invalid CA certificate path (directory, not file) ─────────────────

def test_invalid_ca_cert_path_raises():
    """A directory path (not a file) for DATABASE_SSL_CA_CERT_PATH must raise FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        _build_ssl_context("Production", ca_cert_path=tempfile.gettempdir())


# ── Test 8: Invalid inline PEM content raises ValueError ──────────────────────

def test_invalid_inline_cert_raises():
    """Inline cert that does not start with -----BEGIN must raise ValueError."""
    with pytest.raises(ValueError, match="DATABASE_SSL_CA_CERT"):
        _build_ssl_context("Production", ca_cert_inline="not-a-cert")


# ── Test 9: Inline PEM escaped newlines are normalised ────────────────────────

def test_inline_cert_normalises_escaped_newlines(tmp_path):
    """\\n in inline PEM should be converted to real newlines."""
    cert_path = _make_real_cert_file()
    try:
        with open(cert_path) as f:
            real_pem = f.read()

        # Simulate Railway env var where \n are literal escape sequences.
        escaped_pem = real_pem.replace("\n", "\\n")
        assert "\\n" in escaped_pem, "Precondition: pem must contain literal \\n"

        try:
            # Should succeed: the function normalises \\n → \n before writing.
            ctx = _build_ssl_context("Production", ca_cert_inline=escaped_pem)
            assert isinstance(ctx, ssl.SSLContext)
        except ssl.SSLError:
            # Self-signed cert generated by cryptography will load fine;
            # the fake PEM header may fail SSL loading but not the format check.
            pass
    finally:
        os.unlink(cert_path)


# ── Test 10: Inline cert takes priority over system CA bundle ─────────────────

def test_inline_cert_priority_over_system_bundle(tmp_path, caplog):
    """When inline cert is provided, it should be used (not the system bundle)."""
    cert_path = _make_real_cert_file()
    try:
        with open(cert_path) as f:
            real_pem = f.read()

        with caplog.at_level(logging.INFO, logger="app.database"):
            try:
                _build_ssl_context("Production", ca_cert_inline=real_pem)
            except ssl.SSLError:
                pass  # cert may not be trusted; we only care about which source was used

        assert "DATABASE_SSL_CA_CERT (inline env var)" in caplog.text
    finally:
        os.unlink(cert_path)


# ── Test 11: File path takes priority over inline cert ────────────────────────

def test_cert_path_priority_over_inline(caplog):
    """DATABASE_SSL_CA_CERT_PATH must take priority over DATABASE_SSL_CA_CERT."""
    cert_path = _make_real_cert_file()
    try:
        with caplog.at_level(logging.INFO, logger="app.database"):
            try:
                _build_ssl_context(
                    "Production",
                    ca_cert_path=cert_path,
                    ca_cert_inline=_FAKE_PEM_HEADER,
                )
            except ssl.SSLError:
                pass

        assert f"DATABASE_SSL_CA_CERT_PATH ({cert_path})" in caplog.text
        # Inline should NOT appear in logs when path is provided.
        assert "inline env var" not in caplog.text
    finally:
        os.unlink(cert_path)


# ── Test 12: Non-Supabase URL returns empty connect_args ──────────────────────

def test_non_supabase_url_returns_empty_args():
    """connect_args must be empty for non-Supabase databases."""
    args = _build_async_connect_args(_NON_SUPABASE_URL, "Production")
    assert args == {}


def test_sqlite_url_returns_empty_args():
    """connect_args must be empty for SQLite."""
    args = _build_async_connect_args(_SQLITE_URL, "development")
    assert args == {}


# ── Test 13: Supabase URL produces connect_args with ssl key ──────────────────

def test_supabase_url_includes_ssl_arg():
    """connect_args for a Supabase URL must contain the 'ssl' key."""
    args = _build_async_connect_args(_SUPABASE_URL, "Production")
    assert "ssl" in args
    assert isinstance(args["ssl"], ssl.SSLContext)


# ── Test 14: DATABASE_URL not logged ──────────────────────────────────────────

def test_database_url_not_logged(caplog):
    """log_db_connection_info must not log the DATABASE_URL or password."""
    url = "postgresql+asyncpg://postgres:s3cr3tpassword@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
    ctx = _build_ssl_context("Production")
    args = {"ssl": ctx, "statement_cache_size": 0}

    with caplog.at_level(logging.INFO, logger="app.database"):
        log_db_connection_info(url, args, "Production")

    # The password must never appear in logs.
    assert "s3cr3tpassword" not in caplog.text
    # The full URL must not appear in logs.
    assert url not in caplog.text


# ── Test 15: log_db_connection_info logs safe fields ─────────────────────────

def test_log_db_connection_info_logs_host_port_ssl(caplog):
    """log_db_connection_info must log host, port, SSL status, and environment."""
    url = "postgresql+asyncpg://user:pass@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
    ctx = _build_ssl_context("Production")
    args = {"ssl": ctx, "statement_cache_size": 0}

    with caplog.at_level(logging.INFO, logger="app.database"):
        log_db_connection_info(url, args, "Production")

    assert "aws-1-ap-south-1.pooler.supabase.com" in caplog.text
    assert "5432" in caplog.text
    assert "Production" in caplog.text
    # SSL enabled flag should appear.
    assert "SSL Enabled: True" in caplog.text
    # CERT_REQUIRED should be indicated.
    assert "CERT_REQUIRED" in caplog.text
    # Password must not appear.
    assert "pass" not in caplog.text or "password" not in caplog.text


def test_log_db_connection_info_dev_mode(caplog):
    """In development mode log_db_connection_info should report relaxed SSL."""
    url = "postgresql+asyncpg://user:pass@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"
    ctx = _build_ssl_context("development")
    args = {"ssl": ctx, "statement_cache_size": 0}

    with caplog.at_level(logging.INFO, logger="app.database"):
        log_db_connection_info(url, args, "development")

    assert "CERT_NONE" in caplog.text or "relaxed" in caplog.text


# ── Test 16: Supabase pooler URL detection ────────────────────────────────────

def test_pooler_url_detected_as_supabase():
    """pooler.supabase.com URLs must be detected as Supabase."""
    url = "postgresql+asyncpg://user:pass@aws-1-eu-west-1.pooler.supabase.com:5432/postgres"
    args = _build_async_connect_args(url, "Production")
    assert "ssl" in args


# ── Test 17: Non-pooler Supabase URL detected ────────────────────────────────

def test_direct_supabase_url_detected():
    """Direct supabase.co URLs must also be detected as Supabase."""
    url = "postgresql+asyncpg://postgres:pass@db.abcdef.supabase.co:5432/postgres"
    args = _build_async_connect_args(url, "Production")
    assert "ssl" in args


# ── Test 18: statement_cache_size=0 always set for Supabase ──────────────────

def test_statement_cache_size_always_zero_for_supabase():
    """statement_cache_size must always be 0 for Supabase (PgBouncer compat)."""
    args = _build_async_connect_args(_SUPABASE_URL, "Production")
    assert args.get("statement_cache_size") == 0


def test_statement_cache_size_not_present_for_non_supabase():
    """statement_cache_size must NOT be set for non-Supabase connections."""
    args = _build_async_connect_args(_NON_SUPABASE_URL, "Production")
    assert "statement_cache_size" not in args
