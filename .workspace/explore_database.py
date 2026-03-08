#!/usr/bin/env python3
"""Explore database structure for finance skill."""

import os
import sys
import json

# Add current directory to path to import from skills
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from skills.finance.scripts.sql_query import run_sql_query

def explore_table_structure(table_name):
    """Get column structure of a table."""
    sql = f"""
    SELECT 
        column_name,
        data_type,
        is_nullable,
        character_maximum_length
    FROM information_schema.columns
    WHERE table_name = '{table_name}'
      AND table_schema = 'public'
    ORDER BY ordinal_position;
    """
    
    result = run_sql_query(sql, limit=50)
    data = json.loads(result)
    
    print(f"\n=== Table: {table_name} ===")
    print(f"Columns ({len(data['rows'])}):")
    for row in data['rows']:
        col_info = f"  {row['column_name']}: {row['data_type']}"
        if row['character_maximum_length']:
            col_info += f"({row['character_maximum_length']})"
        col_info += f" [Nullable: {row['is_nullable']}]"
        print(col_info)

def get_sample_data(table_name, limit=5):
    """Get sample data from a table."""
    sql = f"SELECT * FROM {table_name} LIMIT {limit};"
    
    result = run_sql_query(sql, limit=limit)
    data = json.loads(result)
    
    print(f"\n=== Sample data from {table_name} ({len(data['rows'])} rows) ===")
    if data['rows']:
        # Print column headers
        headers = list(data['rows'][0].keys())
        print("Columns:", ", ".join(headers))
        
        # Print sample rows
        for i, row in enumerate(data['rows']):
            print(f"\nRow {i+1}:")
            for key, value in row.items():
                print(f"  {key}: {value}")

def get_table_row_count(table_name):
    """Get row count of a table."""
    sql = f"SELECT COUNT(*) as row_count FROM {table_name};"
    
    result = run_sql_query(sql, limit=1)
    data = json.loads(result)
    
    if data['rows']:
        return data['rows'][0]['row_count']
    return 0

def main():
    print("Exploring finance database...")
    
    # List all tables
    sql = """
    SELECT table_name, 
           (SELECT COUNT(*) FROM information_schema.columns 
            WHERE columns.table_name = tables.table_name) as column_count
    FROM information_schema.tables 
    WHERE table_schema = 'public'
    ORDER BY table_name;
    """
    
    result = run_sql_query(sql, limit=10)
    data = json.loads(result)
    
    print("=== Database Tables ===")
    for row in data['rows']:
        count = get_table_row_count(row['table_name'])
        print(f"{row['table_name']}: {row['column_count']} columns, {count} rows")
    
    # Explore each table
    tables = [row['table_name'] for row in data['rows']]
    
    for table in tables:
        explore_table_structure(table)
        get_sample_data(table, limit=3)
    
    # Get some key statistics
    print("\n=== Key Statistics ===")
    
    # Check cost_database years
    sql = "SELECT DISTINCT year FROM cost_database ORDER BY year;"
    result = run_sql_query(sql, limit=10)
    data = json.loads(result)
    years = [row['year'] for row in data['rows']]
    print(f"Years in cost_database: {', '.join(years)}")
    
    # Check scenarios
    sql = "SELECT DISTINCT scenario FROM cost_database ORDER BY scenario;"
    result = run_sql_query(sql, limit=10)
    data = json.loads(result)
    scenarios = [row['scenario'] for row in data['rows']]
    print(f"Scenarios in cost_database: {', '.join(scenarios)}")
    
    # Check functions
    sql = "SELECT DISTINCT function FROM cost_database ORDER BY function;"
    result = run_sql_query(sql, limit=20)
    data = json.loads(result)
    functions = [row['function'] for row in data['rows']]
    print(f"Functions in cost_database: {', '.join(functions)}")

if __name__ == "__main__":
    main()