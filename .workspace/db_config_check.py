import pyodbc

# 数据库连接配置
server = "Shai438a.ad005.onehc.net"
database = "SmartMES_Demo"
username = "testlogin"
password = "WIN@superman7119"
driver = "SQL Server"

# 测试连接
try:
    conn_str = (
        f"Driver={{{driver}}};"
        f"Server={server};"
        f"Database={database};"
        f"Uid={username};"
        f"Pwd={password};"
    )
    conn = pyodbc.connect(conn_str, timeout=15)
    print("数据库连接成功！")
    conn.close()
except Exception as e:
    print(f"数据库连接失败: {e}")