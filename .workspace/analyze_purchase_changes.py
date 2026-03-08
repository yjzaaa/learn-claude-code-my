import json

# 解析查询结果
fy25_actual_data = {
    "total_cost": 52289546.16,
    "details": [
        {"cost_text": "Procurement", "key": "IM", "total_amount": 2087966.04, "year_total_sum": 25055592.48},
        {"cost_text": "Pooling & MPC", "key": "Pooling", "total_amount": 1922532.96, "year_total_sum": 23070395.52},
        {"cost_text": "GBS P2P", "key": "IM", "total_amount": 346963.18, "year_total_sum": 4163558.16},
        {"cost_text": "SOP SCM", "key": "IM", "total_amount": 0.00, "year_total_sum": 0.00}
    ]
}

fy26_budget_data = {
    "total_cost": 54372000.00,
    "details": [
        {"cost_text": "Procurement", "key": "IM", "total_amount": 2192000.04, "year_total_sum": 26304000.00},
        {"cost_text": "Pooling & MPC", "key": "Pooling", "total_amount": 2019000.00, "year_total_sum": 24228000.00},
        {"cost_text": "GBS P2P", "key": "IM", "total_amount": 320000.04, "year_total_sum": 3840000.00},
        {"cost_text": "SOP SCM", "key": "IM", "total_amount": 0.00, "year_total_sum": 0.00}
    ]
}

# 计算总变化
total_change = fy26_budget_data["total_cost"] - fy25_actual_data["total_cost"]
total_change_percent = (total_change / fy25_actual_data["total_cost"]) * 100

print("=== 26财年采购预算费用与25财年实际数对比分析 ===")
print(f"25财年采购实际费用总计: {fy25_actual_data['total_cost']:,.2f} 元")
print(f"26财年采购预算费用总计: {fy26_budget_data['total_cost']:,.2f} 元")
print(f"绝对变化值: {total_change:,.2f} 元")
print(f"变化率: {total_change_percent:.2f}%")

# 分析各成本项目变化
print("\n=== 各成本项目详细对比 ===")
print(f"{'成本项目':<20} {'25财年实际':<15} {'26财年预算':<15} {'变化值':<15} {'变化率':<10}")
print("-" * 80)

for i in range(len(fy25_actual_data["details"])):
    fy25_item = fy25_actual_data["details"][i]
    fy26_item = fy26_budget_data["details"][i]
    
    cost_text = fy25_item["cost_text"]
    fy25_amount = fy25_item["year_total_sum"]
    fy26_amount = fy26_item["year_total_sum"]
    
    if fy25_amount == 0:
        change_percent = 0 if fy26_amount == 0 else 100
    else:
        change = fy26_amount - fy25_amount
        change_percent = (change / fy25_amount) * 100
    
    print(f"{cost_text:<20} {fy25_amount:>12,.2f}元 {fy26_amount:>12,.2f}元 {fy26_amount - fy25_amount:>12,.2f}元 {change_percent:>8.2f}%")

# 总结分析
print("\n=== 变化分析总结 ===")
if total_change > 0:
    print(f"1. 总体增长: 26财年采购预算比25财年实际费用增加 {total_change:,.2f}元，增长 {total_change_percent:.2f}%")
else:
    print(f"1. 总体下降: 26财年采购预算比25财年实际费用减少 {abs(total_change):,.2f}元，下降 {abs(total_change_percent):.2f}%")

print("\n2. 主要变化项目:")
# 计算各项目变化
changes = []
for i in range(len(fy25_actual_data["details"])):
    fy25_item = fy25_actual_data["details"][i]
    fy26_item = fy26_budget_data["details"][i]
    
    if fy25_item["year_total_sum"] > 0:  # 排除零值项目
        change = fy26_item["year_total_sum"] - fy25_item["year_total_sum"]
        change_percent = (change / fy25_item["year_total_sum"]) * 100
        changes.append({
            "cost_text": fy25_item["cost_text"],
            "change": change,
            "change_percent": change_percent
        })

# 按变化绝对值排序
changes.sort(key=lambda x: abs(x["change"]), reverse=True)

for change in changes:
    if change["change"] > 0:
        print(f"   - {change['cost_text']}: 增加 ¥{change['change']:,.2f} ({change['change_percent']:.2f}%)")
    elif change["change"] < 0:
        print(f"   - {change['cost_text']}: 减少 ¥{abs(change['change']):,.2f} ({abs(change['change_percent']):.2f}%)")
    else:
        print(f"   - {change['cost_text']}: 无变化")

print("\n3. 关键发现:")
print("   - 采购部门总预算呈增长趋势")
print("   - 主要增长来自核心采购业务和Pooling & MPC项目")
print("   - GBS P2P项目预算有所减少")
print("   - SOP SCM项目预算保持为零")