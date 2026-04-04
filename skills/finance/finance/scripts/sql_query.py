"""Database query helper for finance skill (SQL Server + PostgreSQL)."""

import argparse
import json
import os
import re
from pathlib import Path

try:
    from backend.infrastructure.tools.toolkit import tool as _tool_decorator
    _has_tool = True
except ImportError:
    _has_tool = False
    def _tool_decorator(f=None, **kw):  # type: ignore[misc]
        return f if f is not None else (lambda fn: fn)

_ENV_LOADED = False


def _normalize_legacy_sql(sql: str, use_sql_server: bool) -> str:
    """Normalize legacy table/column names to the current schema."""
    normalized = sql

    # Old demo table name still appears in historical prompts/tool traces.
    normalized = re.sub(
        r"\bcost_database\b",
        "dbo.SSME_FI_InsightBot_CostDataBase" if use_sql_server else "cost_database",
        normalized,
        flags=re.IGNORECASE,
    )
    
    # Normalize rate table names
    normalized = re.sub(
        r"\bSSME_FI_InsightBot_Rate\b",
        "rate_table",
        normalized,
        flags=re.IGNORECASE,
    )
    
    # Normalize cc mapping table names
    normalized = re.sub(
        r"\bSSME_FI_InsightBot_CCMapping\b",
        "cc_mapping",
        normalized,
        flags=re.IGNORECASE,
    )
    
    # Normalize column names for rate table
    normalized = re.sub(r"(?<![\w\[])RateNo(?![\w\]])", "rate_no", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"(?<![\w\[])BL(?![\w\]])", "bl", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"(?<![\w\[])CC(?![\w\]])", "cc", normalized, flags=re.IGNORECASE)

    if use_sql_server:
        # SQL Server source table uses spaced, bracketed column names.
        normalized = re.sub(r"(?<![\w\[])year_total(?![\w\]])", "[Year Total]", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![\w\[])year(?![\w\]])", "[Year]", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![\w\[])scenario(?![\w\]])", "[Scenario]", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![\w\[])function(?![\w\]])", "[Function]", normalized, flags=re.IGNORECASE)
        # For SQL Server, keep original column names
        normalized = re.sub(r"(?<![\w\[])rate_no(?![\w\]])", "[RateNo]", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![\w\[])bl(?![\w\]])", "[BL]", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"(?<![\w\[])cc(?![\w\]])", "[CC]", normalized, flags=re.IGNORECASE)

    return normalized


def _find_project_env_file():
    """Find the nearest .env by walking up from this script path."""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def _load_project_env_once() -> None:
    """Load .env values into process environment once (without overriding existing vars)."""
    global _ENV_LOADED
    if _ENV_LOADED:
        return

    env_file = _find_project_env_file()
    if env_file is None:
        _ENV_LOADED = True
        return

    try:
        from dotenv import dotenv_values

        values = dotenv_values(env_file)
        for key, value in values.items():
            if value is None:
                continue
            os.environ.setdefault(str(key), str(value))
    except Exception:
        # Keep query helper resilient even if dotenv is unavailable.
        pass

    _ENV_LOADED = True


@_tool_decorator(
    name="run_sql_query",
    description="Execute a SQL query against the finance database and return the results as JSON. Use this to query cost allocation, budget, actual, and headcount data.",
)
def run_sql_query(sql: str, limit: int = 200) -> str:
    """Execute SQL against configured SQL Server or PostgreSQL."""
    _load_project_env_once()

    if not sql.strip():
        return "Error: Empty SQL query"

    # 标准变量：DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / DB_PORT
    # 兼容旧变量：database_url / database_name / database_username / database_password
    host = os.getenv("DB_HOST") or os.getenv("DB_SERVER") or os.getenv("database_url", "localhost")
    database = os.getenv("DB_NAME") or os.getenv("database_name", "cost_allocation")
    username = os.getenv("DB_USER") or os.getenv("database_username", "postgres")
    password = os.getenv("DB_PASSWORD") or os.getenv("database_password")
    port = os.getenv("DB_PORT") or os.getenv("database_port", "5432")
    db_driver = (os.getenv("DB_DRIVER") or "").strip().lower()

    missing = []
    if not host:
        missing.append("DB_HOST")
    if not database:
        missing.append("DB_NAME")
    if not username:
        missing.append("DB_USER")
    if not password:
        missing.append("DB_PASSWORD")

    if missing:
        return f"Error: Missing DB config in environment: {', '.join(missing)}"

    # Route to SQL Server when explicitly configured (or common SQL Server port is used).
    use_sql_server = "sql server" in db_driver or port == "1433"
    sql = _normalize_legacy_sql(sql, use_sql_server)

    if use_sql_server:
        conn = None
        cursor = None
        try:
            import pyodbc
        except Exception as e:
            return f"Error: pyodbc is required for SQL Server but is not available: {e}"

        odbc_driver = os.getenv("ODBC_DRIVER") or "ODBC Driver 17 for SQL Server"
        conn_str = (
            f"DRIVER={{{odbc_driver}}};"
            f"SERVER={host},{port};"
            f"DATABASE={database};"
            f"UID={username};"
            f"PWD={password};"
            "TrustServerCertificate=yes;"
        )

        try:
            conn = pyodbc.connect(conn_str, timeout=15)
            cursor = conn.cursor()
            cursor.execute(sql)

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchmany(limit)
                data = [dict(zip(columns, row)) for row in rows]
                payload = {
                    "truncated": len(data) >= limit,
                    "limit": limit,
                    "rows": data,
                }
                return json.dumps(payload, ensure_ascii=False, default=str)

            conn.commit()
            return f"OK: {cursor.rowcount} rows affected"
        except Exception as e:
            return f"Error: SQL execution failed: {e}"
        finally:
            try:
                if cursor is not None:
                    cursor.close()
                if conn is not None:
                    conn.close()
            except Exception:
                pass

    conn = None
    cursor = None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=username,
            password=password,
            connect_timeout=15
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(sql)

        if cursor.description:
            rows = cursor.fetchmany(limit)
            # RealDictCursor 返回的是字典类型
            data = [dict(row) for row in rows]
            payload = {
                "truncated": len(data) >= limit,
                "limit": limit,
                "rows": data,
            }
            return json.dumps(payload, ensure_ascii=False, default=str)

        conn.commit()
        return f"OK: {cursor.rowcount} rows affected"
    except Exception as e:
        return f"Error: SQL execution failed: {e}"
    finally:
        try:
            if cursor is not None:
                cursor.close()
            if conn is not None:
                conn.close()
        except Exception:
            pass


def _main() -> int:
    parser = argparse.ArgumentParser(description="Run SQL with finance sql_query helper.")
    parser.add_argument("sql", nargs="?", help="SQL statement to execute")
    parser.add_argument("--sql", dest="sql_kw", help="SQL statement to execute")
    parser.add_argument("--limit", type=int, default=200, help="Max rows to fetch for SELECT")
    args = parser.parse_args()

    sql_text = (args.sql_kw or args.sql or "").strip()
    if not sql_text:
        print("Error: Missing SQL. Use: python skills/finance/scripts/sql_query.py --sql \"SELECT 1\"")
        return 1

    print(run_sql_query(sql_text, limit=args.limit))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
