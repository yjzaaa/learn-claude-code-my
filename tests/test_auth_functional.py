"""Auth API Functional Tests - 认证API功能测试

测试所有认证端点的基本功能是否符合OpenSpec规范。
"""

import asyncio
import time
from typing import Any

import httpx
import pytest

BASE_URL = "http://localhost:8001"


class TestResult:
    """测试结果记录"""

    def __init__(self, name: str):
        self.name = name
        self.status = "PENDING"
        self.status_code = None
        self.response_time_ms = 0
        self.expected = None
        self.actual = None
        self.error = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "status_code": self.status_code,
            "response_time_ms": self.response_time_ms,
            "expected": self.expected,
            "actual": self.actual,
            "error": self.error,
        }


class AuthAPITester:
    """认证API测试器"""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.results: list[TestResult] = []
        self.access_token: str | None = None
        self.refresh_token: str | None = None
        self.client_id: str | None = None
        self.test_username: str = f"testuser_{int(time.time())}"
        self.test_password: str = "testpass123"

    async def close(self):
        await self.client.aclose()

    def _record_result(self, result: TestResult) -> None:
        self.results.append(result)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict | None = None,
        headers: dict | None = None,
    ) -> tuple[int, Any, float]:
        """发送HTTP请求并返回状态码、响应体和响应时间"""
        start = time.time()
        try:
            if method == "GET":
                response = await self.client.get(endpoint, headers=headers)
            elif method == "POST":
                response = await self.client.post(endpoint, json=json_data, headers=headers)
            elif method == "PATCH":
                response = await self.client.patch(endpoint, json=json_data, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            elapsed = (time.time() - start) * 1000
            try:
                body = response.json()
            except Exception:
                body = response.text

            return response.status_code, body, elapsed
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return 0, str(e), elapsed

    # ═════════════════════════════════════════════════════════════════
    # Test Cases
    # ═════════════════════════════════════════════════════════════════

    async def test_auto_login(self) -> TestResult:
        """TC1: POST /api/auth/auto-login - 自动登录（开发模式）"""
        result = TestResult("POST /api/auth/auto-login")
        result.expected = "200 OK with user data and tokens"

        status, body, elapsed = await self._make_request(
            "POST", "/api/auth/auto-login", json_data={}
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 200:
            if isinstance(body, dict) and body.get("success") is True:
                data = body.get("data", {})
                user = data.get("user", {})
                tokens = data.get("tokens", {})

                # 验证响应结构
                if all(k in user for k in ["id", "username", "role"]):
                    if all(k in tokens for k in ["access_token", "refresh_token", "token_type", "expires_in"]):
                        self.access_token = tokens["access_token"]
                        self.refresh_token = tokens["refresh_token"]
                        self.client_id = data.get("client_id")
                        result.status = "PASS"
                        result.actual = f"Login successful, user={user.get('username')}"
                    else:
                        result.status = "FAIL"
                        result.actual = f"Missing token fields: {tokens}"
                else:
                    result.status = "FAIL"
                    result.actual = f"Missing user fields: {user}"
            else:
                result.status = "FAIL"
                result.actual = f"Unexpected response: {body}"
        elif status == 403:
            result.status = "SKIP"
            result.actual = "Auto-login disabled in production (expected in prod)"
        else:
            result.status = "FAIL"
            result.actual = f"HTTP {status}: {body}"

        self._record_result(result)
        return result

    async def test_register(self) -> TestResult:
        """TC2: POST /api/auth/register - 用户注册"""
        result = TestResult("POST /api/auth/register")
        result.expected = "200 OK with new user data"

        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/register",
            json_data={
                "username": self.test_username,
                "password": self.test_password,
                "display_name": "Test User",
            },
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 200:
            if isinstance(body, dict) and body.get("success") is True:
                data = body.get("data", {})
                if all(k in data for k in ["id", "username", "role"]):
                    result.status = "PASS"
                    result.actual = f"Registered user: {data.get('username')} (id={data.get('id')})"
                else:
                    result.status = "FAIL"
                    result.actual = f"Missing fields in response: {data}"
            else:
                result.status = "FAIL"
                result.actual = f"Unexpected response: {body}"
        elif status == 409:
            result.status = "FAIL"
            result.actual = f"User already exists: {body}"
        else:
            result.status = "FAIL"
            result.actual = f"HTTP {status}: {body}"

        self._record_result(result)
        return result

    async def test_login(self) -> TestResult:
        """TC3: POST /api/auth/login - 标准登录"""
        result = TestResult("POST /api/auth/login")
        result.expected = "200 OK with user data and tokens"

        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/login",
            json_data={"username": self.test_username, "password": self.test_password},
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 200:
            if isinstance(body, dict) and body.get("success") is True:
                data = body.get("data", {})
                user = data.get("user", {})
                tokens = data.get("tokens", {})

                if all(k in user for k in ["id", "username", "role"]):
                    if all(k in tokens for k in ["access_token", "refresh_token", "token_type", "expires_in"]):
                        self.access_token = tokens["access_token"]
                        self.refresh_token = tokens["refresh_token"]
                        self.client_id = data.get("client_id")
                        result.status = "PASS"
                        result.actual = f"Login successful, user={user.get('username')}"
                    else:
                        result.status = "FAIL"
                        result.actual = f"Missing token fields: {tokens}"
                else:
                    result.status = "FAIL"
                    result.actual = f"Missing user fields: {user}"
            else:
                result.status = "FAIL"
                result.actual = f"Unexpected response: {body}"
        elif status == 401:
            result.status = "FAIL"
            result.actual = f"Invalid credentials: {body}"
        else:
            result.status = "FAIL"
            result.actual = f"HTTP {status}: {body}"

        self._record_result(result)
        return result

    async def test_login_invalid_credentials(self) -> TestResult:
        """TC4: POST /api/auth/login - 错误凭据"""
        result = TestResult("POST /api/auth/login (invalid credentials)")
        result.expected = "401 Unauthorized"

        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/login",
            json_data={"username": "nonexistent", "password": "wrongpass"},
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 401:
            result.status = "PASS"
            result.actual = f"Correctly rejected with 401: {body.get('detail', body) if isinstance(body, dict) else body}"
        else:
            result.status = "FAIL"
            result.actual = f"Expected 401, got {status}: {body}"

        self._record_result(result)
        return result

    async def test_get_me(self) -> TestResult:
        """TC5: GET /api/auth/me - 获取当前用户"""
        result = TestResult("GET /api/auth/me")
        result.expected = "200 OK with current user data"

        if not self.access_token:
            result.status = "SKIP"
            result.actual = "No access token available (depends on login)"
            self._record_result(result)
            return result

        status, body, elapsed = await self._make_request(
            "GET",
            "/api/auth/me",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 200:
            if isinstance(body, dict) and body.get("success") is True:
                data = body.get("data", {})
                if "id" in data and "username" in data:
                    result.status = "PASS"
                    result.actual = f"Got user: {data.get('username')}"
                else:
                    result.status = "FAIL"
                    result.actual = f"Missing user fields: {data}"
            else:
                result.status = "FAIL"
                result.actual = f"Unexpected response: {body}"
        elif status == 401:
            result.status = "FAIL"
            result.actual = f"Token invalid or expired: {body}"
        else:
            result.status = "FAIL"
            result.actual = f"HTTP {status}: {body}"

        self._record_result(result)
        return result

    async def test_get_me_no_token(self) -> TestResult:
        """TC6: GET /api/auth/me - 无Token"""
        result = TestResult("GET /api/auth/me (no token)")
        result.expected = "401 Unauthorized"

        status, body, elapsed = await self._make_request("GET", "/api/auth/me")

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 401 or status == 403:
            result.status = "PASS"
            result.actual = f"Correctly rejected with {status}"
        else:
            result.status = "FAIL"
            result.actual = f"Expected 401/403, got {status}: {body}"

        self._record_result(result)
        return result

    async def test_refresh_token(self) -> TestResult:
        """TC7: POST /api/auth/refresh - Token刷新"""
        result = TestResult("POST /api/auth/refresh")
        result.expected = "200 OK with new tokens"

        if not self.refresh_token:
            result.status = "SKIP"
            result.actual = "No refresh token available (depends on login)"
            self._record_result(result)
            return result

        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/refresh",
            json_data={"refresh_token": self.refresh_token},
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 200:
            if isinstance(body, dict) and body.get("success") is True:
                data = body.get("data", {})
                if all(k in data for k in ["access_token", "refresh_token", "token_type", "expires_in"]):
                    # 更新token
                    self.access_token = data["access_token"]
                    self.refresh_token = data["refresh_token"]
                    result.status = "PASS"
                    result.actual = "Token refreshed successfully"
                else:
                    result.status = "FAIL"
                    result.actual = f"Missing token fields: {data}"
            else:
                result.status = "FAIL"
                result.actual = f"Unexpected response: {body}"
        elif status == 401:
            result.status = "FAIL"
            result.actual = f"Refresh token invalid or expired: {body}"
        else:
            result.status = "FAIL"
            result.actual = f"HTTP {status}: {body}"

        self._record_result(result)
        return result

    async def test_refresh_invalid_token(self) -> TestResult:
        """TC8: POST /api/auth/refresh - 无效Token"""
        result = TestResult("POST /api/auth/refresh (invalid token)")
        result.expected = "401 Unauthorized"

        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/refresh",
            json_data={"refresh_token": "invalid_token_here"},
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 401:
            result.status = "PASS"
            result.actual = f"Correctly rejected with 401: {body.get('detail', body) if isinstance(body, dict) else body}"
        else:
            result.status = "FAIL"
            result.actual = f"Expected 401, got {status}: {body}"

        self._record_result(result)
        return result

    async def test_logout(self) -> TestResult:
        """TC9: POST /api/auth/logout - 登出"""
        result = TestResult("POST /api/auth/logout")
        result.expected = "200 OK with success message"

        if not self.client_id:
            result.status = "SKIP"
            result.actual = "No client_id available (depends on login)"
            self._record_result(result)
            return result

        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/logout",
            headers={"X-Client-ID": self.client_id},
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 200:
            if isinstance(body, dict) and body.get("success") is True:
                result.status = "PASS"
                result.actual = f"Logout successful: {body.get('message', 'OK')}"
            else:
                result.status = "FAIL"
                result.actual = f"Unexpected response: {body}"
        elif status == 404:
            result.status = "FAIL"
            result.actual = f"Session not found: {body}"
        else:
            result.status = "FAIL"
            result.actual = f"HTTP {status}: {body}"

        self._record_result(result)
        return result

    async def test_logout_no_client_id(self) -> TestResult:
        """TC10: POST /api/auth/logout - 无Client-ID"""
        result = TestResult("POST /api/auth/logout (no client-id)")
        result.expected = "422 Validation Error"

        status, body, elapsed = await self._make_request("POST", "/api/auth/logout")

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 422:
            result.status = "PASS"
            result.actual = f"Correctly rejected with 422 (missing header)"
        else:
            result.status = "FAIL"
            result.actual = f"Expected 422, got {status}: {body}"

        self._record_result(result)
        return result

    async def test_register_duplicate(self) -> TestResult:
        """TC11: POST /api/auth/register - 重复注册"""
        result = TestResult("POST /api/auth/register (duplicate)")
        result.expected = "409 Conflict"

        # 先确保用户存在
        await self._make_request(
            "POST",
            "/api/auth/register",
            json_data={
                "username": self.test_username,
                "password": self.test_password,
                "display_name": "Test User",
            },
        )

        # 再次注册相同用户
        status, body, elapsed = await self._make_request(
            "POST",
            "/api/auth/register",
            json_data={
                "username": self.test_username,
                "password": self.test_password,
                "display_name": "Test User 2",
            },
        )

        result.status_code = status
        result.response_time_ms = round(elapsed, 2)

        if status == 409:
            result.status = "PASS"
            result.actual = f"Correctly rejected with 409: {body.get('detail', body) if isinstance(body, dict) else body}"
        else:
            result.status = "FAIL"
            result.actual = f"Expected 409, got {status}: {body}"

        self._record_result(result)
        return result

    async def run_all_tests(self) -> list[dict]:
        """运行所有测试"""
        print("=" * 70)
        print("Starting Auth API Functional Tests")
        print("=" * 70)

        # 测试执行顺序很重要
        await self.test_auto_login()
        await self.test_register()
        await self.test_login()
        await self.test_login_invalid_credentials()
        await self.test_get_me()
        await self.test_get_me_no_token()
        await self.test_refresh_token()
        await self.test_refresh_invalid_token()
        await self.test_logout()
        await self.test_logout_no_client_id()
        await self.test_register_duplicate()

        return [r.to_dict() for r in self.results]

    def print_report(self) -> None:
        """打印测试报告"""
        print("\n" + "=" * 70)
        print("TEST REPORT")
        print("=" * 70)

        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        skipped = sum(1 for r in self.results if r.status == "SKIP")

        for result in self.results:
            status_symbol = "✓" if result.status == "PASS" else "✗" if result.status == "FAIL" else "○"
            print(f"\n{status_symbol} {result.name}")
            print(f"  Status: {result.status}")
            print(f"  HTTP Status: {result.status_code}")
            print(f"  Response Time: {result.response_time_ms}ms")
            if result.expected:
                print(f"  Expected: {result.expected}")
            print(f"  Actual: {result.actual}")

        print("\n" + "=" * 70)
        print(f"SUMMARY: Total={len(self.results)}, Passed={passed}, Failed={failed}, Skipped={skipped}")
        print("=" * 70)


# ═════════════════════════════════════════════════════════════════
# Pytest Test Functions
# ═════════════════════════════════════════════════════════════════

@pytest.fixture
async def tester():
    """创建测试器fixture"""
    t = AuthAPITester()
    yield t
    await t.close()


@pytest.mark.asyncio
async def test_auth_api_complete():
    """完整的认证API测试"""
    tester = AuthAPITester()
    try:
        await tester.run_all_tests()
        tester.print_report()

        # 断言没有失败的测试
        failed = [r for r in tester.results if r.status == "FAIL"]
        if failed:
            pytest.fail(f"{len(failed)} test(s) failed: {[r.name for r in failed]}")
    finally:
        await tester.close()


# ═════════════════════════════════════════════════════════════════
# Main Entry Point
# ═════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    asyncio.run(test_auth_api_complete())
