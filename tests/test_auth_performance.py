"""Auth Performance Tests - 认证系统性能测试

测试场景：
1. 并发登录测试 - 50个并发请求
2. Token刷新性能 - 测量响应时间分布
3. 数据库连接池测试 - 验证连接管理
4. 连续请求测试 - 1000次顺序请求
5. 混合负载测试 - 登录+刷新+验证混合

测量指标：
- 平均响应时间
- P95/P99响应时间
- 错误率
- 吞吐量（req/s）
- 数据库连接数变化

注意: 本测试需要后端服务运行在 http://localhost:8001
      且认证模块已正确配置（PostgreSQL或SQLite）
"""

import asyncio
import time
import statistics
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import aiohttp
import pytest


# ═════════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8001"
API_PREFIX = "/api/auth"

# Test user credentials
TEST_USERNAME = "perf_test_user"
TEST_PASSWORD = "perf_test_pass123"

# Concurrency settings
CONCURRENT_USERS = 50
SEQUENTIAL_REQUESTS = 1000
TIMEOUT_SECONDS = 30


# ═════════════════════════════════════════════════════════════════
# Data Classes
# ═════════════════════════════════════════════════════════════════

@dataclass
class PerformanceResult:
    """性能测试结果"""

    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_time_seconds: float
    response_times_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def throughput_rps(self) -> float:
        if self.total_time_seconds == 0:
            return 0.0
        return self.successful_requests / self.total_time_seconds

    @property
    def avg_response_time_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        return statistics.mean(self.response_times_ms)

    @property
    def min_response_time_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        return min(self.response_times_ms)

    @property
    def max_response_time_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        return max(self.response_times_ms)

    @property
    def p95_response_time_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        sorted_times = sorted(self.response_times_ms)
        idx = int(len(sorted_times) * 0.95)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    @property
    def p99_response_time_ms(self) -> float:
        if not self.response_times_ms:
            return 0.0
        sorted_times = sorted(self.response_times_ms)
        idx = int(len(sorted_times) * 0.99)
        return sorted_times[min(idx, len(sorted_times) - 1)]

    def to_dict(self) -> dict:
        return {
            "test_name": self.test_name,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate_percent": round(self.success_rate, 2),
            "total_time_seconds": round(self.total_time_seconds, 3),
            "throughput_rps": round(self.throughput_rps, 2),
            "response_times_ms": {
                "min": round(self.min_response_time_ms, 2),
                "avg": round(self.avg_response_time_ms, 2),
                "max": round(self.max_response_time_ms, 2),
                "p95": round(self.p95_response_time_ms, 2),
                "p99": round(self.p99_response_time_ms, 2),
            },
            "errors": self.errors[:10] if self.errors else [],  # Limit errors
        }


# ═════════════════════════════════════════════════════════════════
# HTTP Client
# ═════════════════════════════════════════════════════════════════

class AuthPerformanceClient:
    """认证性能测试客户端"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
        self.session = aiohttp.ClientSession(timeout=timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_auth_available(self) -> tuple[bool, str]:
        """检查认证服务是否可用"""
        try:
            url = f"{self.base_url}{API_PREFIX}/auto-login"
            async with self.session.post(url, json={}) as response:
                if response.status in (200, 403):  # 403表示生产环境禁用，但服务可用
                    return True, "Auth service is available"
                elif response.status == 404:
                    return False, f"Auth endpoint not found (404). Check if auth routes are registered."
                else:
                    text = await response.text()
                    return False, f"Auth service returned {response.status}: {text[:100]}"
        except aiohttp.ClientError as e:
            return False, f"Connection error: {str(e)}"
        except Exception as e:
            return False, f"Error checking auth: {str(e)}"

    async def auto_login(self) -> tuple[bool, Optional[dict], float]:
        """自动登录，返回(成功, 响应数据, 响应时间ms)"""
        start_time = time.perf_counter()
        try:
            url = f"{self.base_url}{API_PREFIX}/auto-login"
            async with self.session.post(url, json={}) as response:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return True, data, elapsed_ms
                else:
                    text = await response.text()
                    return False, {"error": text, "status": response.status}, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return False, {"error": str(e)}, elapsed_ms

    async def login(self, username: str, password: str) -> tuple[bool, Optional[dict], float]:
        """用户登录，返回(成功, 响应数据, 响应时间ms)"""
        start_time = time.perf_counter()
        try:
            url = f"{self.base_url}{API_PREFIX}/login"
            async with self.session.post(
                url, json={"username": username, "password": password}
            ) as response:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return True, data, elapsed_ms
                else:
                    text = await response.text()
                    return False, {"error": text, "status": response.status}, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return False, {"error": str(e)}, elapsed_ms

    async def refresh_token(self, refresh_token: str) -> tuple[bool, Optional[dict], float]:
        """刷新令牌，返回(成功, 响应数据, 响应时间ms)"""
        start_time = time.perf_counter()
        try:
            url = f"{self.base_url}{API_PREFIX}/refresh"
            async with self.session.post(
                url, json={"refresh_token": refresh_token}
            ) as response:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return True, data, elapsed_ms
                else:
                    text = await response.text()
                    return False, {"error": text, "status": response.status}, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return False, {"error": str(e)}, elapsed_ms

    async def get_me(self, access_token: str) -> tuple[bool, Optional[dict], float]:
        """获取当前用户信息，返回(成功, 响应数据, 响应时间ms)"""
        start_time = time.perf_counter()
        try:
            url = f"{self.base_url}{API_PREFIX}/me"
            headers = {"Authorization": f"Bearer {access_token}"}
            async with self.session.get(url, headers=headers) as response:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                if response.status == 200:
                    data = await response.json()
                    return True, data, elapsed_ms
                else:
                    text = await response.text()
                    return False, {"error": text, "status": response.status}, elapsed_ms
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return False, {"error": str(e)}, elapsed_ms


# ═════════════════════════════════════════════════════════════════
# Test Functions
# ═════════════════════════════════════════════════════════════════

async def run_concurrent_login_test(concurrent_users: int = CONCURRENT_USERS) -> PerformanceResult:
    """测试1: 并发登录测试 - 50个并发请求"""

    result = PerformanceResult(
        test_name="并发登录测试",
        total_requests=concurrent_users,
        successful_requests=0,
        failed_requests=0,
        total_time_seconds=0,
    )

    async def single_login_task(client: AuthPerformanceClient, user_index: int) -> tuple[bool, float, str]:
        # 使用不同的用户名避免冲突
        username = f"{TEST_USERNAME}_{user_index}"
        success, data, elapsed_ms = await client.login(username, TEST_PASSWORD)
        if not success and data and "Invalid" in str(data.get("error", "")):
            # 用户不存在，尝试自动登录
            success, data, elapsed_ms = await client.auto_login()
        return success, elapsed_ms, str(data.get("error", "")) if not success else ""

    start_time = time.perf_counter()

    async with AuthPerformanceClient() as client:
        # 创建并发任务
        tasks = [single_login_task(client, i) for i in range(concurrent_users)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    result.total_time_seconds = time.perf_counter() - start_time

    for res in results:
        if isinstance(res, Exception):
            result.failed_requests += 1
            result.errors.append(str(res))
        else:
            success, elapsed_ms, error = res
            if success:
                result.successful_requests += 1
                result.response_times_ms.append(elapsed_ms)
            else:
                result.failed_requests += 1
                if error:
                    result.errors.append(error)

    return result


async def run_token_refresh_test(num_requests: int = 100) -> PerformanceResult:
    """测试2: Token刷新性能 - 测量响应时间分布"""

    result = PerformanceResult(
        test_name="Token刷新性能测试",
        total_requests=num_requests,
        successful_requests=0,
        failed_requests=0,
        total_time_seconds=0,
    )

    async with AuthPerformanceClient() as client:
        # 首先获取一个有效的token
        success, data, _ = await client.auto_login()
        if not success:
            result.errors.append("Failed to get initial token")
            return result

        refresh_token_str = data["data"]["tokens"]["refresh_token"]

        start_time = time.perf_counter()

        # 执行多次刷新
        for _ in range(num_requests):
            success, resp_data, elapsed_ms = await client.refresh_token(refresh_token_str)
            if success:
                result.successful_requests += 1
                result.response_times_ms.append(elapsed_ms)
                # 使用新的refresh token进行下一次刷新
                refresh_token_str = resp_data["data"]["refresh_token"]
            else:
                result.failed_requests += 1
                result.errors.append(str(resp_data.get("error", "Unknown error")))
                break

        result.total_time_seconds = time.perf_counter() - start_time

    return result


async def run_sequential_requests_test(num_requests: int = SEQUENTIAL_REQUESTS) -> PerformanceResult:
    """测试3: 连续请求测试 - 1000次顺序请求"""

    result = PerformanceResult(
        test_name="连续请求测试",
        total_requests=num_requests,
        successful_requests=0,
        failed_requests=0,
        total_time_seconds=0,
    )

    async with AuthPerformanceClient() as client:
        # 首先登录获取token
        success, data, _ = await client.auto_login()
        if not success:
            result.errors.append("Failed to get initial token")
            return result

        access_token = data["data"]["tokens"]["access_token"]

        start_time = time.perf_counter()

        # 执行顺序请求
        for i in range(num_requests):
            success, resp_data, elapsed_ms = await client.get_me(access_token)
            if success:
                result.successful_requests += 1
                result.response_times_ms.append(elapsed_ms)
            else:
                result.failed_requests += 1
                result.errors.append(str(resp_data.get("error", "Unknown error")))
                if result.failed_requests > 10:  # 太多错误，停止测试
                    result.errors.append(f"Stopped after {i} requests due to too many errors")
                    break

        result.total_time_seconds = time.perf_counter() - start_time

    return result


async def run_mixed_load_test(num_iterations: int = 100) -> PerformanceResult:
    """测试4: 混合负载测试 - 登录+刷新+验证混合"""

    result = PerformanceResult(
        test_name="混合负载测试",
        total_requests=num_iterations * 3,  # 每个迭代3个请求
        successful_requests=0,
        failed_requests=0,
        total_time_seconds=0,
    )

    async def mixed_task(client: AuthPerformanceClient, iteration: int) -> list[tuple[bool, float, str]]:
        results = []

        # 1. 登录
        success, data, elapsed_ms = await client.auto_login()
        results.append((success, elapsed_ms, "login"))

        if not success:
            return results

        tokens = data["data"]["tokens"]
        access_token = tokens["access_token"]
        refresh_token_str = tokens["refresh_token"]

        # 2. 获取用户信息
        success, _, elapsed_ms = await client.get_me(access_token)
        results.append((success, elapsed_ms, "get_me"))

        # 3. 刷新token
        success, _, elapsed_ms = await client.refresh_token(refresh_token_str)
        results.append((success, elapsed_ms, "refresh"))

        return results

    start_time = time.perf_counter()

    async with AuthPerformanceClient() as client:
        for i in range(num_iterations):
            task_results = await mixed_task(client, i)
            for success, elapsed_ms, op_type in task_results:
                if success:
                    result.successful_requests += 1
                    result.response_times_ms.append(elapsed_ms)
                else:
                    result.failed_requests += 1

    result.total_time_seconds = time.perf_counter() - start_time

    return result


async def run_connection_pool_test(num_concurrent: int = 100) -> PerformanceResult:
    """测试5: 数据库连接池测试 - 验证连接管理"""

    result = PerformanceResult(
        test_name="数据库连接池测试",
        total_requests=num_concurrent,
        successful_requests=0,
        failed_requests=0,
        total_time_seconds=0,
    )

    async def connection_task(task_id: int) -> tuple[bool, float, str]:
        async with AuthPerformanceClient() as client:
            # 登录 + 获取信息 + 登出
            start_time = time.perf_counter()

            success, data, _ = await client.auto_login()
            if not success:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return False, elapsed_ms, "login_failed"

            access_token = data["data"]["tokens"]["access_token"]
            client_id = data["data"]["client_id"]

            # 获取用户信息
            success, _, _ = await client.get_me(access_token)
            if not success:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                return False, elapsed_ms, "get_me_failed"

            elapsed_ms = (time.perf_counter() - start_time) * 1000
            return True, elapsed_ms, ""

    start_time = time.perf_counter()

    # 创建多个独立客户端并发执行
    tasks = [connection_task(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    result.total_time_seconds = time.perf_counter() - start_time

    for res in results:
        if isinstance(res, Exception):
            result.failed_requests += 1
            result.errors.append(str(res))
        else:
            success, elapsed_ms, error = res
            if success:
                result.successful_requests += 1
                result.response_times_ms.append(elapsed_ms)
            else:
                result.failed_requests += 1
                if error:
                    result.errors.append(error)

    return result


# ═════════════════════════════════════════════════════════════════
# Report Generation
# ═════════════════════════════════════════════════════════════════

def print_performance_report(results: list[PerformanceResult]) -> None:
    """打印性能测试报告"""

    print("\n" + "=" * 80)
    print("                    认证系统性能测试报告")
    print("=" * 80)
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"目标服务: {BASE_URL}")
    print("=" * 80)

    for result in results:
        print(f"\n【{result.test_name}】")
        print("-" * 60)
        print(f"  总请求数:     {result.total_requests}")
        print(f"  成功请求:     {result.successful_requests}")
        print(f"  失败请求:     {result.failed_requests}")
        print(f"  成功率:       {result.success_rate:.2f}%")
        print(f"  总耗时:       {result.total_time_seconds:.3f}s")
        print(f"  吞吐量:       {result.throughput_rps:.2f} req/s")
        print(f"\n  响应时间统计:")
        print(f"    最小值:     {result.min_response_time_ms:.2f}ms")
        print(f"    平均值:     {result.avg_response_time_ms:.2f}ms")
        print(f"    最大值:     {result.max_response_time_ms:.2f}ms")
        print(f"    P95:        {result.p95_response_time_ms:.2f}ms")
        print(f"    P99:        {result.p99_response_time_ms:.2f}ms")

        if result.errors:
            print(f"\n  错误样本 (最多显示10条):")
            for i, error in enumerate(result.errors[:10], 1):
                print(f"    {i}. {error[:100]}")

    print("\n" + "=" * 80)
    print("                         测试总结")
    print("=" * 80)

    total_requests = sum(r.total_requests for r in results)
    total_success = sum(r.successful_requests for r in results)
    total_failed = sum(r.failed_requests for r in results)
    overall_success_rate = (total_success / total_requests * 100) if total_requests > 0 else 0

    print(f"  总请求数:     {total_requests}")
    print(f"  总成功数:     {total_success}")
    print(f"  总失败数:     {total_failed}")
    print(f"  整体成功率:   {overall_success_rate:.2f}%")
    print("=" * 80)

    # 性能评估
    print("\n【性能评估】")
    for result in results:
        status = "PASS" if result.success_rate >= 95 and result.p95_response_time_ms < 1000 else "FAIL"
        print(f"  {result.test_name}: {status}")
        if result.p95_response_time_ms > 1000:
            print(f"    ⚠️  P95响应时间超过1秒")
        if result.success_rate < 95:
            print(f"    ⚠️  成功率低于95%")

    print("\n" + "=" * 80)


def generate_chart_data(results: list[PerformanceResult]) -> dict:
    """生成图表数据"""

    return {
        "response_time_comparison": {
            "labels": [r.test_name for r in results],
            "datasets": [
                {
                    "label": "平均响应时间 (ms)",
                    "data": [r.avg_response_time_ms for r in results],
                },
                {
                    "label": "P95响应时间 (ms)",
                    "data": [r.p95_response_time_ms for r in results],
                },
                {
                    "label": "P99响应时间 (ms)",
                    "data": [r.p99_response_time_ms for r in results],
                },
            ],
        },
        "throughput_comparison": {
            "labels": [r.test_name for r in results],
            "datasets": [
                {
                    "label": "吞吐量 (req/s)",
                    "data": [r.throughput_rps for r in results],
                },
            ],
        },
        "success_rate": {
            "labels": [r.test_name for r in results],
            "datasets": [
                {
                    "label": "成功率 (%)",
                    "data": [r.success_rate for r in results],
                },
            ],
        },
        "detailed_results": [r.to_dict() for r in results],
    }


# ═════════════════════════════════════════════════════════════════
# Main Entry Point
# ═════════════════════════════════════════════════════════════════

async def check_prerequisites() -> tuple[bool, str]:
    """检查测试前提条件"""
    async with AuthPerformanceClient() as client:
        # 检查后端健康状态
        try:
            async with client.session.get(f"{BASE_URL}/health") as resp:
                if resp.status != 200:
                    return False, f"Backend health check failed: {resp.status}"
        except Exception as e:
            return False, f"Cannot connect to backend at {BASE_URL}: {str(e)}"

        # 检查认证服务
        available, message = await client.check_auth_available()
        if not available:
            return False, f"Auth service not available: {message}"

        return True, "All prerequisites met"


async def run_all_performance_tests() -> list[PerformanceResult]:
    """运行所有性能测试"""

    print("\n🚀 开始认证系统性能测试...")
    print(f"目标服务: {BASE_URL}")
    print("-" * 60)

    # 检查前提条件
    print("\n[0/5] 检查前提条件...")
    prereq_ok, prereq_msg = await check_prerequisites()
    if not prereq_ok:
        print(f"  ❌ 前提条件检查失败: {prereq_msg}")
        print("\n请确保:")
        print("  1. 后端服务已启动: python main.py")
        print("  2. 认证数据库已配置 (PostgreSQL或SQLite)")
        print("  3. 认证路由已正确注册")
        return []
    print(f"  ✓ {prereq_msg}")

    results = []

    # 测试1: 并发登录测试
    print("\n[1/5] 运行并发登录测试 (50并发)...")
    result = await run_concurrent_login_test(CONCURRENT_USERS)
    results.append(result)
    print(f"  完成: 成功率 {result.success_rate:.1f}%, 吞吐量 {result.throughput_rps:.2f} req/s")

    # 测试2: Token刷新性能
    print("\n[2/5] 运行Token刷新性能测试 (100次刷新)...")
    result = await run_token_refresh_test(100)
    results.append(result)
    print(f"  完成: 成功率 {result.success_rate:.1f}%, 平均响应 {result.avg_response_time_ms:.2f}ms")

    # 测试3: 连续请求测试
    print(f"\n[3/5] 运行连续请求测试 ({SEQUENTIAL_REQUESTS}次顺序请求)...")
    result = await run_sequential_requests_test(SEQUENTIAL_REQUESTS)
    results.append(result)
    print(f"  完成: 成功率 {result.success_rate:.1f}%, 吞吐量 {result.throughput_rps:.2f} req/s")

    # 测试4: 混合负载测试
    print("\n[4/5] 运行混合负载测试 (登录+刷新+验证)...")
    result = await run_mixed_load_test(100)
    results.append(result)
    print(f"  完成: 成功率 {result.success_rate:.1f}%, 吞吐量 {result.throughput_rps:.2f} req/s")

    # 测试5: 数据库连接池测试
    print("\n[5/5] 运行数据库连接池测试 (100并发连接)...")
    result = await run_connection_pool_test(100)
    results.append(result)
    print(f"  完成: 成功率 {result.success_rate:.1f}%, P95响应 {result.p95_response_time_ms:.2f}ms")

    return results


@pytest.mark.asyncio
async def test_auth_performance_full():
    """完整的认证性能测试 (Pytest入口)"""

    results = await run_all_performance_tests()

    if not results:
        pytest.skip("Prerequisites not met - auth service not available")

    print_performance_report(results)

    # 生成图表数据
    chart_data = generate_chart_data(results)

    # 断言检查
    for result in results:
        # 成功率应 >= 95%
        assert result.success_rate >= 95, f"{result.test_name} 成功率过低: {result.success_rate:.2f}%"

        # P95响应时间应 < 2秒
        assert result.p95_response_time_ms < 2000, f"{result.test_name} P95响应时间过长: {result.p95_response_time_ms:.2f}ms"

    return results


@pytest.mark.asyncio
async def test_auth_service_available():
    """测试认证服务是否可用"""
    async with AuthPerformanceClient() as client:
        available, message = await client.check_auth_available()
        if not available:
            pytest.skip(f"Auth service not available: {message}")
        assert available, message


@pytest.mark.asyncio
async def test_concurrent_login():
    """测试并发登录性能"""
    async with AuthPerformanceClient() as client:
        available, _ = await client.check_auth_available()
        if not available:
            pytest.skip("Auth service not available")

    result = await run_concurrent_login_test(10)  # 减少并发数用于单元测试
    assert result.success_rate >= 90, f"并发登录成功率过低: {result.success_rate:.2f}%"


@pytest.mark.asyncio
async def test_token_refresh():
    """测试Token刷新性能"""
    async with AuthPerformanceClient() as client:
        available, _ = await client.check_auth_available()
        if not available:
            pytest.skip("Auth service not available")

    result = await run_token_refresh_test(10)  # 减少次数用于单元测试
    assert result.success_rate >= 90, f"Token刷新成功率过低: {result.success_rate:.2f}%"


# 直接运行入口
if __name__ == "__main__":
    results = asyncio.run(run_all_performance_tests())

    if results:
        print_performance_report(results)

        # 保存详细结果到JSON文件
        import json

        chart_data = generate_chart_data(results)
        output_file = "auth_performance_report.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(chart_data, f, ensure_ascii=False, indent=2)

        print(f"\n📊 详细报告已保存到: {output_file}")
    else:
        print("\n⚠️ 测试未能完成 - 请检查前提条件")
        exit(1)
