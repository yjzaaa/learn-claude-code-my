"""SQL Server query helper for finance skill."""

import json
import os


def run_sql_query(sql: str, limit: int = 200) -> str:
    """Execute SQL against configured SQL Server via pyodbc."""
    try:
        import pyodbc
    except Exception as e:
        return f"Error: pyodbc is not available: {e}"

    # 标准变量：DB_SERVER / DB_NAME / DB_USER / DB_PASSWORD / DB_DRIVER
    # 兼容旧变量：database_url / database_name / database_username / database_password
    server = os.getenv("DB_SERVER") or os.getenv("database_url")
    database = os.getenv("DB_NAME") or os.getenv("database_name")
    username = os.getenv("DB_USER") or os.getenv("database_username")
    password = os.getenv("DB_PASSWORD") or os.getenv("database_password")
    driver = os.getenv("DB_DRIVER", "SQL Server")
    port = os.getenv("DB_PORT") or os.getenv("database_port")

    missing = []
    if not server:
        missing.append("DB_SERVER")
    if not database:
        missing.append("DB_NAME")
    if not username:
        missing.append("DB_USER")
    if not password:
        missing.append("DB_PASSWORD")

    if missing:
        return f"Error: Missing DB config in environment: {', '.join(missing)}"

    server_endpoint = f"{server},{port}" if port and "," not in server else server

    conn_str = (
        f"Driver={{{driver}}};"
        f"Server={server_endpoint};"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
    )

    cursor = None
    conn = None
    try:
        conn = pyodbc.connect(conn_str, timeout=15)
        cursor = conn.cursor()
        cursor.execute(sql)

        if cursor.description:
            cols = [col[0] for col in cursor.description]
            rows = cursor.fetchmany(limit)
            data = [dict(zip(cols, row)) for row in rows]
            payload = {
                "truncated": len(data) >= limit,
                "limit": limit,
                "rows": data,
            }
            return json.dumps(payload, ensure_ascii=False)

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
