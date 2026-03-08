#!/usr/bin/env python3
"""Finance query tool based on finance skill templates."""

import os
import sys
import json
import re

# Add current directory to path to import from skills
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from skills.finance.scripts.sql_query import run_sql_query

class FinanceQueryTool:
    """Finance query tool implementing the finance skill templates."""
    
    def __init__(self):
        self.normalization_map = {
            # 版本归一化
            '预算': 'Budget1',
            '实际': 'Actual',
            '预测': 'Rolling Forecast2',
            'Budget': 'Budget1',
            'Actual': 'Actual',
            'Forecast': 'Rolling Forecast2',
            
            # 职能归一化
            'HR': 'HR',
            'IT': 'IT',
            '采购': 'Procurement',
            'Procurement': 'Procurement',
            
            # 分摊函数映射
            'IT分摊': 'IT Allocation',
            'HR分摊': 'HR Allocation',
            '采购分摊': 'Procurement Allocation',
        }
    
    def normalize_param(self, param):
        """Normalize parameter values."""
        param = param.strip()
        return self.normalization_map.get(param, param)
    
    def detect_query_type(self, question):
        """Detect query type from question."""
        question_lower = question.lower()
        
        if '分摊给' in question or 'allocated to' in question_lower:
            return 'allocation'
        elif '对比' in question or '比变化' in question or '差异' in question:
            return 'comparison'
        elif '趋势' in question or '变化趋势' in question:
            return 'trend'
        else:
            return 'cost'
    
    def extract_parameters(self, question):
        """Extract parameters from question."""
        params = {
            'year': None,
            'scenario': None,
            'function': None,
            'target': None,
            'target_type': None,  # 'bl' or 'cc'
        }
        
        # Extract year
        year_pattern = r'FY(\d{2})'
        year_match = re.search(year_pattern, question, re.IGNORECASE)
        if year_match:
            params['year'] = f"FY{year_match.group(1)}"
        
        # Extract scenario
        if '预算' in question or 'Budget' in question:
            params['scenario'] = 'Budget1'
        elif '实际' in question or 'Actual' in question:
            params['scenario'] = 'Actual'
        elif '预测' in question or 'Forecast' in question:
            params['scenario'] = 'Rolling Forecast2'
        
        # Extract function
        if 'HR' in question or '人力资源' in question:
            params['function'] = 'HR'
        elif 'IT' in question:
            params['function'] = 'IT'
        elif '采购' in question or 'Procurement' in question:
            params['function'] = 'Procurement'
        
        # Extract allocation target
        allocation_match = re.search(r'分摊给\s*(\w+)', question)
        if allocation_match:
            params['target'] = allocation_match.group(1)
            # Check if target is a cost center (all digits) or business line
            if params['target'].isdigit():
                params['target_type'] = 'cc'
            else:
                params['target_type'] = 'bl'
        
        return params
    
    def query_cost_summary(self, year, scenario, function):
        """Query cost summary (Template 1)."""
        sql = f"""
        SELECT
            function,
            cost_text,
            key,
            SUM(amount) as total_amount
        FROM cost_database
        WHERE year = '{year}'
          AND scenario = '{scenario}'
          AND function = '{function}'
        GROUP BY function, cost_text, key
        ORDER BY total_amount DESC;
        """
        
        result = run_sql_query(sql, limit=50)
        return json.loads(result)
    
    def query_allocation(self, year, scenario, function, target, target_type):
        """Query allocation amount (Template 2)."""
        # Determine allocation function and key
        if function == 'IT':
            allocation_function = 'IT Allocation'
            allocation_key = '480056 Cycle'
        elif function == 'HR':
            allocation_function = 'HR Allocation'
            allocation_key = '480055 Cycle'
        elif function == 'Procurement':
            allocation_function = 'Procurement Allocation'
            allocation_key = 'Procurement Cycle'
        else:
            return {"error": f"Unknown function for allocation: {function}"}
        
        # Build target condition
        if target_type == 'bl':
            target_condition = f"rt.bl = '{target}'"
        elif target_type == 'cc':
            target_condition = f"rt.cc = '{target}'"
        else:
            return {"error": f"Unknown target type: {target_type}"}
        
        sql = f"""
        SELECT
            cdb.month,
            cdb.amount as base_cost,
            rt.rate_no,
            (cdb.amount * rt.rate_no / 100.0) as allocated_amount
        FROM cost_database cdb
        JOIN rate_table rt ON cdb.month = rt.month
            AND cdb.year = rt.year
            AND cdb.scenario = rt.scenario
            AND cdb.key = rt.key
        WHERE cdb.year = '{year}'
          AND cdb.scenario = '{scenario}'
          AND cdb.function = '{allocation_function}'
          AND rt.key = '{allocation_key}'
          AND {target_condition}
        ORDER BY cdb.month;
        """
        
        result = run_sql_query(sql, limit=100)
        return json.loads(result)
    
    def query_comparison(self, year1, scenario1, year2, scenario2, function):
        """Query comparison between two periods (Template 3)."""
        sql = f"""
        -- First period data
        SELECT '{year1} {scenario1}' as period, SUM(amount) as total
        FROM cost_database
        WHERE year = '{year1}' AND scenario = '{scenario1}' AND function = '{function}'
        
        UNION ALL
        
        -- Second period data
        SELECT '{year2} {scenario2}', SUM(amount)
        FROM cost_database
        WHERE year = '{year2}' AND scenario = '{scenario2}' AND function = '{function}';
        """
        
        result = run_sql_query(sql, limit=10)
        return json.loads(result)
    
    def query_cost_centers(self, business_line):
        """Query cost centers for a business line (Template 4)."""
        sql = f"""
        SELECT DISTINCT cc
        FROM rate_table
        WHERE bl = '{business_line}'
        ORDER BY cc;
        """
        
        result = run_sql_query(sql, limit=50)
        return json.loads(result)
    
    def execute_query(self, question):
        """Execute query based on question."""
        query_type = self.detect_query_type(question)
        params = self.extract_parameters(question)
        
        print(f"Query type: {query_type}")
        print(f"Parameters: {params}")
        
        if query_type == 'cost':
            if not all([params['year'], params['scenario'], params['function']]):
                return {"error": "Missing parameters for cost query"}
            
            result = self.query_cost_summary(
                params['year'], 
                params['scenario'], 
                params['function']
            )
            
            # Calculate total
            total = sum(row.get('total_amount', 0) for row in result.get('rows', []))
            result['total_summary'] = {
                'year': params['year'],
                'scenario': params['scenario'],
                'function': params['function'],
                'total_amount': total
            }
            
            return result
            
        elif query_type == 'allocation':
            if not all([params['year'], params['scenario'], params['function'], params['target'], params['target_type']]):
                return {"error": "Missing parameters for allocation query"}
            
            result = self.query_allocation(
                params['year'],
                params['scenario'],
                params['function'],
                params['target'],
                params['target_type']
            )
            
            # Calculate total allocation
            total_allocation = sum(row.get('allocated_amount', 0) for row in result.get('rows', []))
            result['allocation_summary'] = {
                'year': params['year'],
                'scenario': params['scenario'],
                'function': params['function'],
                'target': params['target'],
                'target_type': params['target_type'],
                'total_allocated': total_allocation
            }
            
            return result
            
        elif query_type == 'comparison':
            # For simplicity, assume comparison between two years
            if not all([params['year'], params['scenario'], params['function']]):
                return {"error": "Missing parameters for comparison query"}
            
            # Try to find another year for comparison
            # Get all available years
            sql = "SELECT DISTINCT year FROM cost_database ORDER BY year;"
            years_result = run_sql_query(sql, limit=10)
            years_data = json.loads(years_result)
            years = [row['year'] for row in years_data.get('rows', [])]
            
            if len(years) < 2:
                return {"error": "Need at least two years for comparison"}
            
            # Use current year and previous year
            current_year = params['year']
            year_index = years.index(current_year) if current_year in years else -1
            
            if year_index > 0:
                prev_year = years[year_index - 1]
            elif year_index < len(years) - 1:
                prev_year = years[year_index + 1]
            else:
                prev_year = years[0] if years[0] != current_year else years[1] if len(years) > 1 else None
            
            if not prev_year:
                return {"error": "Cannot find another year for comparison"}
            
            result = self.query_comparison(
                prev_year, params['scenario'],
                current_year, params['scenario'],
                params['function']
            )
            
            # Calculate change
            rows = result.get('rows', [])
            if len(rows) >= 2:
                old_value = rows[0].get('total', 0)
                new_value = rows[1].get('total', 0)
                change = new_value - old_value
                change_percent = (change / old_value * 100) if old_value != 0 else 0
                
                result['comparison_summary'] = {
                    'period1': rows[0].get('period'),
                    'period2': rows[1].get('period'),
                    'old_value': old_value,
                    'new_value': new_value,
                    'change': change,
                    'change_percent': change_percent
                }
            
            return result
        
        else:
            return {"error": f"Unsupported query type: {query_type}"}

def main():
    """Main function with example queries."""
    tool = FinanceQueryTool()
    
    # Example queries
    example_queries = [
        "FY25 HR预算多少？",
        "FY24 IT实际费用？",
        "FY25 IT分摊给CT的费用？",
        "FY26 HR分摊给成本中心412001的费用？",
        "FY25采购预算和FY24实际比变化多少？",
    ]
    
    print("Finance Query Tool - Example Queries")
    print("=" * 50)
    
    for i, query in enumerate(example_queries, 1):
        print(f"\n{i}. Query: {query}")
        print("-" * 30)
        
        try:
            result = tool.execute_query(query)
            
            if 'error' in result:
                print(f"Error: {result['error']}")
                continue
            
            # Print summary if available
            if 'total_summary' in result:
                summary = result['total_summary']
                print(f"Total {summary['function']} {summary['scenario']} for {summary['year']}: {summary['total_amount']:,.2f}")
            
            elif 'allocation_summary' in result:
                summary = result['allocation_summary']
                print(f"Total {summary['function']} allocated to {summary['target']} ({summary['target_type']}): {summary['total_allocated']:,.2f}")
                
                # Show monthly breakdown
                rows = result.get('rows', [])
                if rows:
                    print("\nMonthly breakdown (first 3 months):")
                    for row in rows[:3]:
                        print(f"  {row['month']}: Base={row['base_cost']:,.2f}, Rate={row['rate_no']}, Allocated={row['allocated_amount']:,.2f}")
            
            elif 'comparison_summary' in result:
                summary = result['comparison_summary']
                print(f"Comparison: {summary['period1']} vs {summary['period2']}")
                print(f"  {summary['period1']}: {summary['old_value']:,.2f}")
                print(f"  {summary['period2']}: {summary['new_value']:,.2f}")
                print(f"  Change: {summary['change']:,.2f} ({summary['change_percent']:.2f}%)")
            
            # Show row count
            rows = result.get('rows', [])
            print(f"\nRows returned: {len(rows)}")
            
        except Exception as e:
            print(f"Error executing query: {e}")
    
    # Interactive mode
    print("\n" + "=" * 50)
    print("Interactive Mode - Enter your own queries")
    print("Type 'exit' to quit")
    print("=" * 50)
    
    while True:
        try:
            user_query = input("\nEnter finance query (Chinese or English): ").strip()
            
            if user_query.lower() in ['exit', 'quit', 'q']:
                break
            
            if not user_query:
                continue
            
            print(f"\nProcessing: {user_query}")
            result = tool.execute_query(user_query)
            
            if 'error' in result:
                print(f"Error: {result['error']}")
                continue
            
            # Print summary
            if 'total_summary' in result:
                summary = result['total_summary']
                print(f"\n📊 Total {summary['function']} {summary['scenario']} for {summary['year']}:")
                print(f"   Amount: {summary['total_amount']:,.2f}")
                
                # Show breakdown
                rows = result.get('rows', [])
                if rows:
                    print(f"\nBreakdown by cost_text/key:")
                    for row in rows[:5]:  # Show top 5
                        print(f"  • {row['cost_text']} ({row['key']}): {row['total_amount']:,.2f}")
                    if len(rows) > 5:
                        print(f"  ... and {len(rows) - 5} more items")
            
            elif 'allocation_summary' in result:
                summary = result['allocation_summary']
                print(f"\n📊 {summary['function']} Allocation to {summary['target']} ({summary['year']} {summary['scenario']}):")
                print(f"   Total Allocated: {summary['total_allocated']:,.2f}")
                
                # Show monthly details
                rows = result.get('rows', [])
                if rows:
                    print(f"\nMonthly Allocation Details:")
                    total_base = sum(row.get('base_cost', 0) for row in rows)
                    print(f"  Total Base Cost: {total_base:,.2f}")
                    
                    # Show by month
                    for row in rows:
                        month = row['month']
                        base = row.get('base_cost', 0)
                        rate = row.get('rate_no', 0)
                        allocated = row.get('allocated_amount', 0)
                        print(f"  {month}: Base={base:,.2f}, Rate={rate}, Allocated={allocated:,.2f}")
            
            elif 'comparison_summary' in result:
                summary = result['comparison_summary']
                print(f"\n📊 Comparison Analysis:")
                print(f"  {summary['period1']}: {summary['old_value']:,.2f}")
                print(f"  {summary['period2']}: {summary['new_value']:,.2f}")
                print(f"  Change: {summary['change']:,.2f} ({summary['change_percent']:.2f}%)")
                
                if summary['change'] > 0:
                    print(f"  📈 Increase of {abs(summary['change_percent']):.2f}%")
                elif summary['change'] < 0:
                    print(f"  📉 Decrease of {abs(summary['change_percent']):.2f}%")
                else:
                    print(f"  ➖ No change")
            
            else:
                # Generic output
                rows = result.get('rows', [])
                print(f"\nQuery returned {len(rows)} rows")
                if rows:
                    print("\nFirst few rows:")
                    for i, row in enumerate(rows[:3]):
                        print(f"  Row {i+1}: {row}")
                    if len(rows) > 3:
                        print(f"  ... and {len(rows) - 3} more rows")
                        
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()