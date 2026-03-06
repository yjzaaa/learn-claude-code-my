from query_table_structure import query_table_structure

def query_ct_table_structure():
    table_name = "SSME_FI_InsightBot_CostDataBase"  # 假设的表名
    result = query_table_structure(table_name)
    return result

if __name__ == "__main__":
    output = query_ct_table_structure()
    print(output)