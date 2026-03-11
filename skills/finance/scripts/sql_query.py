"""Database query helper for finance skill (SQL Server + PostgreSQL)."""

import argparse
import json
import os
import re
from pathlib import Path

_ENV_LOADED = False


def _build_error_payload(code: str, message: str, *, stage: str, sql: str | None = None, reasons: list[dict] | None = None) -> str:
    """Return machine-readable error payload for model-side handling."""
    payload = {
        "ok": False,
        "stage": stage,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if sql is not None:
        payload["sql"] = sql
    if reasons:
        payload["error"]["reasons"] = reasons
    return json.dumps(payload, ensure_ascii=False)


def _has_unbalanced_single_quotes(sql: str) -> bool:
    """Check for unbalanced single quotes while handling escaped '' pairs."""
    in_string = False
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'":
            if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_string = not in_string
        i += 1
    return in_string


def _has_unbalanced_parentheses(sql: str) -> bool:
    """Check parentheses balance outside single-quoted strings."""
    depth = 0
    in_string = False
    i = 0
    while i < len(sql):
        char = sql[i]
        if char == "'":
            if in_string and i + 1 < len(sql) and sql[i + 1] == "'":
                i += 2
                continue
            in_string = not in_string
            i += 1
            continue
        if not in_string:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth < 0:
                    return True
        i += 1
    return in_string or depth != 0


def _validate_sql_query(sql: str) -> dict:
    """Validate SQL before execution and return structured reasons on failure."""
    reasons: list[dict] = []
    trimmed = sql.strip()

    if not trimmed:
        reasons.append(
            {
                "code": "EMPTY_SQL",
                "message": "SQL is empty.",
                "detail": "Provide a non-empty SELECT/WITH query.",
            }
        )
        return {"valid": False, "reasons": reasons}

    # Allow one optional trailing semicolon only.
    without_trailing = re.sub(r";\s*$", "", trimmed)
    if ";" in without_trailing:
        reasons.append(
            {
                "code": "MULTI_STATEMENT",
                "message": "Multiple SQL statements are not allowed.",
                "detail": "Only a single statement is supported.",
            }
        )

    if not re.match(r"^(select|with)\b", without_trailing, flags=re.IGNORECASE):
        reasons.append(
            {
                "code": "INVALID_START",
                "message": "SQL must start with SELECT or WITH.",
                "detail": "DDL/DML/EXEC statements are not allowed.",
            }
        )

    if not re.search(r"\bselect\b", without_trailing, flags=re.IGNORECASE):
        reasons.append(
            {
                "code": "MISSING_SELECT",
                "message": "Only query statements are allowed.",
                "detail": "SQL must contain a SELECT clause.",
            }
        )

    forbidden_patterns = [
        (r"\b(drop|truncate|alter|create)\b", "DDL_NOT_ALLOWED", "DDL statements are not allowed."),
        (r"\b(delete|update|insert|merge)\b", "DML_NOT_ALLOWED", "Data modification statements are not allowed."),
        (r"\b(exec|execute)\b", "EXEC_NOT_ALLOWED", "EXEC statements are not allowed."),
        (r"\b(begin|commit|rollback|savepoint)\b", "TRANSACTION_NOT_ALLOWED", "Transaction control statements are not allowed."),
        (r"\b(call|do|copy)\b", "PROCEDURE_NOT_ALLOWED", "Procedure or bulk execution statements are not allowed."),
        (r"\bselect\b[\s\S]*\binto\b\s+[#\[\]`\"\w]", "SELECT_INTO_NOT_ALLOWED", "SELECT INTO is not allowed in query-only mode."),
    ]

    for pattern, code, message in forbidden_patterns:
        if re.search(pattern, without_trailing, flags=re.IGNORECASE):
            reasons.append(
                {
                    "code": code,
                    "message": message,
                    "detail": f"Matched pattern: {pattern}",
                }
            )

    if _has_unbalanced_single_quotes(without_trailing):
        reasons.append(
            {
                "code": "UNBALANCED_QUOTES",
                "message": "Single quotes are not balanced.",
                "detail": "Check string literals and escaped quotes.",
            }
        )

    if _has_unbalanced_parentheses(without_trailing):
        reasons.append(
            {
                "code": "UNBALANCED_PARENTHESES",
                "message": "Parentheses are not balanced.",
                "detail": "Check opening and closing parentheses.",
            }
        )

    return {"valid": len(reasons) == 0, "reasons": reasons}



def _find_project_env_file() -> Path | None:
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


def run_sql_query(sql: str, limit: int = 200) -> str:
    """Execute SQL against configured SQL Server or PostgreSQL."""
    _load_project_env_once()

    validation = _validate_sql_query(sql)
    if not validation["valid"]:
        return _build_error_payload(
            "SQL_VALIDATION_FAILED",
            "SQL failed validation before execution.",
            stage="validation",
            sql=sql,
            reasons=validation["reasons"],
        )

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
        return _build_error_payload(
            "MISSING_DB_CONFIG",
            f"Missing DB config in environment: {', '.join(missing)}",
            stage="configuration",
            sql=sql,
        )

    # Route to SQL Server when explicitly configured (or common SQL Server port is used).
    use_sql_server = "sql server" in db_driver or port == "1433"
    # sql = _normalize_legacy_sql(sql, use_sql_server)

    if use_sql_server:
        conn = None
        cursor = None
        try:
            import pyodbc
        except Exception as e:
            return _build_error_payload(
                "MISSING_DRIVER",
                f"pyodbc is required for SQL Server but is not available: {e}",
                stage="configuration",
                sql=sql,
            )

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

            return _build_error_payload(
                "QUERY_ONLY_ENFORCED",
                "Only query statements that return a result set are allowed.",
                stage="validation",
                sql=sql,
                reasons=[
                    {
                        "code": "NO_RESULT_SET",
                        "message": "Statement did not return a result set.",
                        "detail": "Use a SELECT/WITH query that returns rows.",
                    }
                ],
            )
        except Exception as e:
            return _build_error_payload(
                "SQL_EXECUTION_FAILED",
                f"SQL execution failed: {e}",
                stage="execution",
                sql=sql,
            )
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

        return _build_error_payload(
            "QUERY_ONLY_ENFORCED",
            "Only query statements that return a result set are allowed.",
            stage="validation",
            sql=sql,
            reasons=[
                {
                    "code": "NO_RESULT_SET",
                    "message": "Statement did not return a result set.",
                    "detail": "Use a SELECT/WITH query that returns rows.",
                }
            ],
        )
    except Exception as e:
        return _build_error_payload(
            "SQL_EXECUTION_FAILED",
            f"SQL execution failed: {e}",
            stage="execution",
            sql=sql,
        )
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
