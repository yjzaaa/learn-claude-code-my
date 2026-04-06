import sys
from pathlib import Path

# 添加当前目录到模块搜索路径
_scripts_dir = Path(__file__).parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

from allocation_utils import generate_alloc_sql


def build_sql() -> str:
    return generate_alloc_sql(
        years=["FY26", "FY25"],
        scenarios=["Budget1", "Actual"],
        function_name="HR Allocation",
        party_field="t7.[CC]",
        party_value="413001",
    )


if __name__ == "__main__":
    print(build_sql())
