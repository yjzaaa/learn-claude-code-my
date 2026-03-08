#!/usr/bin/env python3
"""
查询26财年HR费用预算的脚本
"""

import psycopg2
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def get_db_connection():
    """获取数据库连接"""
    try:
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'cost_allocation'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '123456')
        )
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return None

def query_table_structure(conn, table_name):
    """查询表结构"""
    try:
        cursor = conn.cursor()
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable
        FROM information_schema.columns
        WHERE table_name = %s
          AND table_schema = 'public'
        ORDER BY ordinal_position;
        """
        cursor.execute(query, (table_name,))
        columns = cursor.fetchall()
        cursor.close()
        
        print(f"\n{table_name} 表结构:")
        print("-" * 50)
        for col in columns:
            print(f"{col[0]:20} | {col[1]:15} | {col[2]}")
        print("-" * 50)
        return columns
    except Exception as e:
        print(f"查询表结构失败: {e}")
        return []

def query_hr_budget_fy26(conn):
    """查询26财年HR预算"""
    try:
        cursor = conn.cursor()
        
        # 先查询表结构
        print("正在查询表结构...")
        columns = query_table_structure(conn, 'cost_database')
        
        # 查询26财年HR预算
        query = """
        SELECT 
            function,
            cost_text,
            key,
            SUM(year_total) as total_budget
        FROM cost_database
        WHERE year = 'FY26'
          AND scenario = 'Budget1'
          AND function = 'HR'
        GROUP BY function, cost_text, key
        ORDER BY total_budget DESC;
        """
        
        print("\n正在查询26财年HR预算...")
        cursor.execute(query)
        results = cursor.fetchall()
        
        print("\n26财年HR预算明细:")
        print("=" * 80)
        print(f"{'职能':<10} | {'成本项目':<30} | {'分摊标准':<15} | {'预算金额':>15}")
        print("-" * 80)
        
        total_budget = 0
        for row in results:
            function, cost_text, key, amount = row
            print(f"{function:<10} | {cost_text:<30} | {key:<15} | {amount:>15,.2f}")
            total_budget += amount if amount else 0
        
        print("-" * 80)
        print(f"{'总计':<10} | {'':<30} | {'':<15} | {total_budget:>15,.2f}")
        print("=" * 80)
        
        cursor.close()
        return total_budget
        
    except Exception as e:
        print(f"查询失败: {e}")
        return None

def main():
    """主函数"""
    print("开始查询26财年HR费用预算...")
    
    # 获取数据库连接
    conn = get_db_connection()
    if not conn:
        print("无法连接到数据库，请检查环境变量配置")
        return
    
    try:
        # 查询HR预算
        total_budget = query_hr_budget_fy26(conn)
        
        if total_budget is not None:
            print(f"\n26财年HR费用总预算: {total_budget:,.2f}")
        else:
            print("\n未能获取到26财年HR预算数据")
            
    finally:
        conn.close()
        print("\n数据库连接已关闭")

if __name__ == "__main__":
    main()