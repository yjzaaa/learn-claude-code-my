"""PostgreSQL query helper for finance skill."""

import json
import os


def run_sql_query(sql: str, limit: int = 200) -> str:
    """Execute SQL against configured PostgreSQL via psycopg2."""
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except Exception as e:
        return f"Error: psycopg2 is not available: {e}"
    if not sql.strip():
        return "Error: Empty SQL query"
    # 标准变量：DB_HOST / DB_NAME / DB_USER / DB_PASSWORD / DB_PORT
    # 兼容旧变量：database_url / database_name / database_username / database_password
    host = os.getenv("DB_HOST") or os.getenv("DB_SERVER") or os.getenv("database_url", "localhost")
    database = os.getenv("DB_NAME") or os.getenv("database_name", "cost_allocation")
    username = os.getenv("DB_USER") or os.getenv("database_username", "postgres")
    password = os.getenv("DB_PASSWORD") or os.getenv("database_password", "123456")
    port = os.getenv("DB_PORT") or os.getenv("database_port", "5432")

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

    conn = None
    cursor = None
    try:
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
