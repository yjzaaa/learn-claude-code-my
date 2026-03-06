import pyodbc

# 数据库连接配置
server = "Shai438a.ad005.onehc.net"
database = "SmartMES_Demo"
username = "testlogin"
password = "WIN@superman7119"
driver = "SQL Server"

# 定义调试 SQL 查询
sql_query = """
SELECT TOP 10 *
FROM SSME_FI_InsightBot_CostDataBase cdb
WHERE cdb.[Year] = 'FY25'
    AND cdb.[Scenario] = 'Actual'
    AND cdb.[Function] = 'IT Allocation'
    AND cdb.[Key] = 'CT';
"""

# 执行 SQL 查询
try:
    conn_str = (
        f"Driver={{{driver}}};"
        f"Server={server};"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
    )
    conn = pyodbc.connect(conn_str, timeout=15)
    cursor = conn.cursor()
    cursor.execute(sql_query)

    # 获取查询结果
    cols = [col[0] for col in cursor.description]
    rows = cursor.fetchall()
    for row in rows:
        print(dict(zip(cols, row)))

    cursor.close()
    conn.close()
except Exception as e:
    print(f"SQL 执行失败: {e}")