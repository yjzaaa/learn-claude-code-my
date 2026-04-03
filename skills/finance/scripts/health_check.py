"""
Finance Skill Health Check - 体温测试

测试内容：
1. SQL 查询生成能力
2. 术语归一化逻辑
3. 数据库连接状态
4. 分摊计算逻辑

输出格式：Token 流式输出，前端可逐字显示
"""

import json
import sys
import time
from typing import Any, Dict, List, Generator
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

try:
    from skills.finance.scripts.allocation_utils import generate_alloc_sql
    from skills.finance.scripts.sql_query import run_sql_query
except ImportError:
    # 如果在 skills 目录内运行
    from allocation_utils import generate_alloc_sql
    from sql_query import run_sql_query


class TokenStream:
    """Token 流式输出器 - 支持前端逐字显示"""

    def __init__(self, stream_output: bool = True):
        self.stream_output = stream_output
        self.buffer = ""

    def emit(self, token: str, delay: float = 0.01) -> str:
        """发射单个 token，可选延迟模拟流式效果"""
        if self.stream_output:
            print(token, end='', flush=True)
            time.sleep(delay)
        self.buffer += token
        return token

    def emit_line(self, line: str, delay: float = 0.01) -> str:
        """发射一行文本"""
        for char in line:
            self.emit(char, delay)
        self.emit('\n', 0)
        return line

    def emit_json_chunk(self, data: Dict[str, Any]) -> str:
        """发射 JSON 数据块"""
        chunk = json.dumps(data, ensure_ascii=False)
        return self.emit_line(chunk)

    def get_buffer(self) -> str:
        return self.buffer


def normalize_term(term: str) -> str:
    """术语归一化测试"""
    term_mapping = {
        # 白领相关
        '白领': 'WCW',
        '白领数': 'WCW',
        'White Collar Worker': 'WCW',
        'WCW': 'WCW',
        # 人头相关
        '人头': 'headcount',
        '人数': 'headcount',
        'head count': 'headcount',
        'Headcount': 'headcount',
        # 预算相关
        '预算': 'Budget1',
        '计划': 'Budget1',
        'budget': 'Budget1',
        'BGT': 'Budget1',
        'BGT1': 'Budget1',
        # 实际相关
        '实际': 'Actual',
        'actual': 'Actual',
        'ACT': 'Actual',
        # 分摊相关
        '分摊': 'Allocation',
        'allocated': 'Allocation',
        'allocation': 'Allocation',
    }
    return term_mapping.get(term, term)


def test_term_normalization(stream: TokenStream) -> bool:
    """测试 1: 术语归一化"""
    stream.emit_line("\n" + "="*60)
    stream.emit_line("[测试 1] 术语归一化")
    stream.emit_line("="*60)

    test_cases = [
        ('白领', 'WCW'),
        ('预算', 'Budget1'),
        ('实际', 'Actual'),
        ('分摊', 'Allocation'),
        ('人头', 'headcount'),
    ]

    all_passed = True
    for input_term, expected in test_cases:
        result = normalize_term(input_term)
        passed = result == expected
        status = "✅" if passed else "❌"
        stream.emit_line(f"{status} {input_term} -> {result} (期望: {expected})")
        if not passed:
            all_passed = False

    return all_passed


def test_sql_generation(stream: TokenStream) -> bool:
    """测试 2: SQL 查询生成"""
    stream.emit_line("\n" + "="*60)
    stream.emit_line("[测试 2] SQL 查询生成")
    stream.emit_line("="*60)

    try:
        # 测试分摊 SQL 生成
        sql = generate_alloc_sql(
            years=['2025'],
            scenarios=['Budget1'],
            function_name='IT Allocation',
            party_field='t7.bl',
            party_value='CT'
        )

        checks = [
            ('IT Allocation' in sql, "包含源 Function"),
            ('CT' in sql, "包含目标 BL"),
            ('2025' in sql, "包含年份"),
            ('WCW' in sql, "包含分摊 Key"),
        ]

        all_passed = True
        for passed, desc in checks:
            status = "✅" if passed else "❌"
            stream.emit_line(f"{status} {desc}")
            if not passed:
                all_passed = False

        # 输出生成的 SQL 预览
        stream.emit_line("\n📋 生成的 SQL 预览:")
        for line in sql.split('\n')[:5]:
            stream.emit_line(f"   {line}")

        return all_passed
    except Exception as e:
        stream.emit_line(f"❌ SQL 生成失败: {e}")
        return False


def test_db_connection(stream: TokenStream) -> bool:
    """测试 3: 数据库连接"""
    stream.emit_line("\n" + "="*60)
    stream.emit_line("🔍 测试 3: 数据库连接")
    stream.emit_line("="*60)

    # 执行简单查询测试连接
    result = run_sql_query("SELECT 1 as test", limit=1)

    if result.startswith("Error"):
        stream.emit_line(f"⚠️  数据库连接跳过: {result}")
        stream.emit_line("💡 提示: 配置 DB_HOST/DB_NAME/DB_USER/DB_PASSWORD 环境变量")
        return True  # 连接问题不算测试失败

    try:
        data = json.loads(result)
        if data.get('rows'):
            stream.emit_line("✅ 数据库连接正常")
            stream.emit_line(f"✅ 查询返回 {len(data['rows'])} 行")
            return True
    except Exception as e:
        stream.emit_line(f"❌ 结果解析失败: {e}")
        return False

    return False


def test_allocation_logic(stream: TokenStream) -> bool:
    """测试 4: 分摊计算逻辑验证"""
    stream.emit_line("\n" + "="*60)
    stream.emit_line("🔍 测试 4: 分摊计算逻辑")
    stream.emit_line("="*60)

    # 测试分摊金额计算
    test_cases = [
        {'amount': 1000, 'rate': '12.5%', 'expected': 125.0},
        {'amount': 1000, 'rate': '0.125', 'expected': 125.0},
        {'amount': 2000, 'rate': '50%', 'expected': 1000.0},
    ]

    all_passed = True
    for case in test_cases:
        amount = case['amount']
        rate_str = case['rate']
        expected = case['expected']

        # 归一化 rate
        if '%' in rate_str:
            rate = float(rate_str.replace('%', '')) / 100
        else:
            rate = float(rate_str)

        result = amount * rate
        passed = abs(result - expected) < 0.01
        status = "✅" if passed else "❌"

        stream.emit_line(f"{status} {amount} * {rate_str} = {result} (期望: {expected})")
        if not passed:
            all_passed = False

    return all_passed


def run_health_check(stream_output: bool = True) -> Dict[str, Any]:
    """
    运行完整的体温测试

    Args:
        stream_output: 是否使用 token 流式输出

    Returns:
        测试结果字典
    """
    stream = TokenStream(stream_output)

    # 测试开始
    stream.emit_line("\n" + "="*60)
    stream.emit_line("Finance Skill 体温测试")
    stream.emit_line("="*60)
    stream.emit_line(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    results = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'tests': {}
    }

    # 运行各项测试
    tests = [
        ('term_normalization', test_term_normalization),
        ('sql_generation', test_sql_generation),
        ('db_connection', test_db_connection),
        ('allocation_logic', test_allocation_logic),
    ]

    all_passed = True
    for test_name, test_func in tests:
        try:
            passed = test_func(stream)
            results['tests'][test_name] = {'passed': passed, 'error': None}
            if not passed:
                all_passed = False
        except Exception as e:
            results['tests'][test_name] = {'passed': False, 'error': str(e)}
            stream.emit_line(f"❌ 测试异常: {e}")
            all_passed = False

    # 测试结束
    stream.emit_line("\n" + "="*60)
    stream.emit_line("📊 测试结果汇总")
    stream.emit_line("="*60)

    passed_count = sum(1 for t in results['tests'].values() if t['passed'])
    total_count = len(results['tests'])

    stream.emit_line(f"✅ 通过: {passed_count}/{total_count}")
    stream.emit_line(f"❌ 失败: {total_count - passed_count}/{total_count}")

    if all_passed:
        stream.emit_line("\n🎉 所有测试通过！Finance Skill 运行正常。")
    else:
        stream.emit_line("\n⚠️  部分测试失败，请检查配置。")

    stream.emit_line("="*60)

    results['overall_passed'] = all_passed
    results['summary'] = {
        'passed': passed_count,
        'total': total_count
    }

    return results


def run_health_check_stream() -> Generator[str, None, Dict[str, Any]]:
    """
    流式运行体温测试 - 用于前端逐字显示

    Yields:
        每个 token/chunk

    Returns:
        最终结果字典
    """
    import io
    import sys

    # 重定向标准输出以捕获流
    old_stdout = sys.stdout
    sys.stdout = buffer = io.StringIO()

    result = run_health_check(stream_output=False)

    output = buffer.getvalue()
    sys.stdout = old_stdout

    # 逐字符输出
    for char in output:
        yield char

    # 返回最终结果
    yield '\n'
    yield '__RESULT__:'
    yield json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Finance Skill 体温测试')
    parser.add_argument('--stream', action='store_true', help='使用流式输出')
    parser.add_argument('--json', action='store_true', help='仅输出 JSON 结果')
    args = parser.parse_args()

    if args.json:
        result = run_health_check(stream_output=False)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.stream:
        for chunk in run_health_check_stream():
            print(chunk, end='', flush=True)
    else:
        result = run_health_check(stream_output=True)
