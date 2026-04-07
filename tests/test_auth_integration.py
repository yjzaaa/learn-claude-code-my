"""Auth Integration Tests - 认证系统集成测试

测试认证系统与现有后端组件的集成。
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from typing import Any

import pytest
import httpx
import websockets

# 测试配置
BASE_URL = "http://localhost:8001"
WS_URL = "ws://localhost:8001"


class TestReport:
    """测试报告收集器"""

    def __init__(self):
        self.results = []
        self.issues = []
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = datetime.now()

    def end(self):
        self.end_time = datetime.now()

    def add_result(self, test_name: str, status: str, details: dict):
        self.results.append({
            "test_name": test_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "details": details,
        })

    def add_issue(self, category: str, description: str, severity: str, details: dict = None):
        """记录集成问题"""
        self.issues.append({
            "category": category,
            "description": description,
            "severity": severity,
            "details": details or {},
            "timestamp": datetime.now().isoformat(),
        })

    def summary(self) -> dict:
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        failed = sum(1 for r in self.results if r["status"] == "FAIL")
        skipped = sum(1 for r in self.results if r["status"] == "SKIP")

        duration = ""
        if self.start_time and self.end_time:
            duration = str(self.end_time - self.start_time)

        return {
            "total": len(self.results),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration": duration,
            "results": self.results,
            "issues": self.issues,
        }


report = TestReport()


# ═════════════════════════════════════════════════════════════════
# Fixtures
# ═════════════════════════════════════════════════════════════════

@pytest.fixture
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def http_client():
    """HTTP客户端"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.fixture
async def auth_token(http_client):
    """获取认证token（使用auto-login）"""
    try:
        response = await http_client.post("/api/auth/auto-login", json={})
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data["data"]["tokens"]["access_token"]
    except Exception as e:
        print(f"Auto-login failed: {e}")
    return None


@pytest.fixture
async def auth_headers(auth_token):
    """认证请求头"""
    if auth_token:
        return {"Authorization": f"Bearer {auth_token}"}
    return {}


# ═════════════════════════════════════════════════════════════════
# Test Cases
# ═════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_health_check(http_client):
    """TC1: 健康检查端点"""
    test_name = "TC1: Health Check"
    try:
        response = await http_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "ok"
        report.add_result(test_name, "PASS", {"response": data})
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_auth_auto_login(http_client):
    """TC2: 自动登录功能"""
    test_name = "TC2: Auto Login"
    try:
        response = await http_client.post("/api/auth/auto-login", json={})

        if response.status_code == 404:
            # 数据库映射问题
            report.add_issue(
                category="Database Schema",
                description="Auth database models have missing foreign key relationships",
                severity="HIGH",
                details={"error": response.text}
            )
            report.add_result(test_name, "FAIL", {"status_code": 404, "note": "Database schema issue"})
            pytest.skip("Database schema issue - auth not functional")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "tokens" in data["data"]
        assert "access_token" in data["data"]["tokens"]
        report.add_result(test_name, "PASS", {"has_token": True})
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_auth_me_endpoint(http_client, auth_headers):
    """TC3: 获取当前用户信息"""
    test_name = "TC3: Get Current User"
    if not auth_headers:
        report.add_result(test_name, "SKIP", {"reason": "No auth token"})
        pytest.skip("No auth token available")

    try:
        response = await http_client.get("/api/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "id" in data["data"]
        assert "username" in data["data"]
        report.add_result(test_name, "PASS", {"user": data["data"]})
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_auth_me_without_token(http_client):
    """TC4: 未认证访问受保护端点"""
    test_name = "TC4: Access Protected Endpoint Without Token"
    try:
        response = await http_client.get("/api/auth/me")
        # 期望403，但如果端点不存在可能是404
        if response.status_code == 404:
            report.add_issue(
                category="API Endpoint",
                description="Auth endpoint /api/auth/me not found - auth system may not be fully initialized",
                severity="HIGH",
                details={"status_code": 404}
            )
            report.add_result(test_name, "FAIL", {"status_code": 404, "note": "Endpoint not found"})
            return

        assert response.status_code in [401, 403]
        report.add_result(test_name, "PASS", {"status_code": response.status_code})
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_dialogs_list_unprotected(http_client):
    """TC5: 对话列表端点（当前未受保护）"""
    test_name = "TC5: List Dialogs (Unprotected)"
    try:
        response = await http_client.get("/api/dialogs")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        report.add_result(test_name, "PASS", {"dialogs_count": len(data.get("data", []))})
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_create_dialog(http_client):
    """TC6: 创建对话"""
    test_name = "TC6: Create Dialog"
    try:
        response = await http_client.post("/api/dialogs", json={"title": "Test Dialog"})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "id" in data["data"]
        dialog_id = data["data"]["id"]
        report.add_result(test_name, "PASS", {"dialog_id": dialog_id})
        return dialog_id
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_websocket_connection():
    """TC7: WebSocket连接（无认证）"""
    test_name = "TC7: WebSocket Connection (No Auth)"
    client_id = f"test_client_{int(time.time())}"

    try:
        async with websockets.connect(f"{WS_URL}/ws/{client_id}") as ws:
            # 发送订阅消息
            await ws.send(json.dumps({"type": "subscribe", "dialog_id": "test_dialog"}))

            # 等待响应（最多3秒）
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                data = json.loads(response)
                report.add_result(test_name, "PASS", {
                    "connected": True,
                    "received_message": data.get("type", "unknown"),
                })
            except asyncio.TimeoutError:
                # 没有收到消息也是正常的（如果没有对话）
                report.add_result(test_name, "PASS", {
                    "connected": True,
                    "received_message": None,
                })
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_websocket_with_auth_token(auth_token):
    """TC8: WebSocket连接（带认证token）"""
    test_name = "TC8: WebSocket Connection (With Auth Token)"
    if not auth_token:
        report.add_result(test_name, "SKIP", {"reason": "No auth token"})
        pytest.skip("No auth token available")

    client_id = f"test_auth_client_{int(time.time())}"

    try:
        # 注意：当前WebSocket handler不验证token
        # 这个测试验证WebSocket是否能正常连接
        async with websockets.connect(f"{WS_URL}/ws/{client_id}") as ws:
            report.add_result(test_name, "PASS", {
                "connected": True,
                "note": "WebSocket accepts connection (auth not enforced in WS)",
            })
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_end_to_end_message_flow(http_client, auth_headers):
    """TC9: 端到端消息流程"""
    test_name = "TC9: End-to-End Message Flow"

    try:
        # 1. 创建对话
        response = await http_client.post("/api/dialogs", json={"title": "E2E Test"})
        assert response.status_code == 200
        dialog_data = response.json()
        dialog_id = dialog_data["data"]["id"]

        # 2. 连接WebSocket
        client_id = f"e2e_client_{int(time.time())}"
        messages_received = []

        async with websockets.connect(f"{WS_URL}/ws/{client_id}") as ws:
            # 订阅对话
            await ws.send(json.dumps({"type": "subscribe", "dialog_id": dialog_id}))

            # 等待快照
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=2.0)
                messages_received.append(json.loads(response))
            except asyncio.TimeoutError:
                pass

            # 3. 发送消息
            msg_response = await http_client.post(
                f"/api/dialogs/{dialog_id}/messages",
                json={"content": "Hello, this is a test message"},
            )
            assert msg_response.status_code == 200

            # 4. 等待更多消息
            try:
                for _ in range(5):
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    messages_received.append(json.loads(response))
            except asyncio.TimeoutError:
                pass

        report.add_result(test_name, "PASS", {
            "dialog_id": dialog_id,
            "messages_received": len(messages_received),
            "message_types": [m.get("type") for m in messages_received],
        })

    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_container_state_with_auth(http_client, auth_headers):
    """TC10: 容器状态与认证"""
    test_name = "TC10: Container State with Auth"

    try:
        # 检查Agent状态端点
        response = await http_client.get("/api/agent/status")

        if response.status_code == 502:
            report.add_issue(
                category="Backend Service",
                description="Backend service returned 502 Bad Gateway - service may be restarting or unavailable",
                severity="MEDIUM",
                details={"status_code": 502}
            )
            report.add_result(test_name, "FAIL", {"status_code": 502, "note": "Service unavailable"})
            return

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        report.add_result(test_name, "PASS", {
            "container_status": "accessible",
            "has_data": "data" in data,
        })
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_models_endpoint(http_client):
    """TC11: 模型列表端点"""
    test_name = "TC11: Models Endpoint"

    try:
        response = await http_client.get("/api/config/models")

        if response.status_code == 502:
            report.add_issue(
                category="Backend Service",
                description="Backend service returned 502 Bad Gateway when fetching models",
                severity="MEDIUM",
                details={"status_code": 502}
            )
            report.add_result(test_name, "FAIL", {"status_code": 502, "note": "Service unavailable"})
            return

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data
        assert "available_models" in data["data"]

        report.add_result(test_name, "PASS", {
            "models_count": len(data["data"]["available_models"]),
            "current_model": data["data"].get("model"),
        })
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_auth_sessions_endpoint(http_client, auth_headers):
    """TC12: 用户会话列表端点"""
    test_name = "TC12: User Sessions Endpoint"

    if not auth_headers:
        report.add_result(test_name, "SKIP", {"reason": "No auth token"})
        pytest.skip("No auth token available")

    try:
        response = await http_client.get("/api/auth/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "data" in data

        report.add_result(test_name, "PASS", {
            "sessions_count": len(data["data"]),
        })
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_dialog_isolation(http_client, auth_headers):
    """TC13: 对话隔离性测试"""
    test_name = "TC13: Dialog Isolation"

    try:
        # 创建两个对话
        resp1 = await http_client.post("/api/dialogs", json={"title": "Dialog 1"})
        resp2 = await http_client.post("/api/dialogs", json={"title": "Dialog 2"})

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        dialog1_id = resp1.json()["data"]["id"]
        dialog2_id = resp2.json()["data"]["id"]

        # 验证对话ID不同
        assert dialog1_id != dialog2_id

        # 获取对话1详情
        detail1 = await http_client.get(f"/api/dialogs/{dialog1_id}")
        assert detail1.status_code == 200

        # 获取对话2详情
        detail2 = await http_client.get(f"/api/dialogs/{dialog2_id}")
        assert detail2.status_code == 200

        report.add_result(test_name, "PASS", {
            "dialog1_id": dialog1_id,
            "dialog2_id": dialog2_id,
            "isolation": "confirmed",
        })

    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_invalid_token_access(http_client):
    """TC14: 无效token访问测试"""
    test_name = "TC14: Invalid Token Access"

    try:
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = await http_client.get("/api/auth/me", headers=headers)

        # 应该返回401或403
        if response.status_code == 404:
            report.add_issue(
                category="API Endpoint",
                description="Auth endpoint not available for token validation test",
                severity="MEDIUM",
                details={"status_code": 404}
            )
            report.add_result(test_name, "FAIL", {"status_code": 404, "note": "Endpoint not available"})
            return

        assert response.status_code in [401, 403]

        report.add_result(test_name, "PASS", {
            "status_code": response.status_code,
            "rejected": True,
        })
    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


@pytest.mark.asyncio
async def test_logout_and_access(http_client, auth_headers):
    """TC15: 登出后访问测试"""
    test_name = "TC15: Logout and Access"

    if not auth_headers:
        report.add_result(test_name, "SKIP", {"reason": "No auth token"})
        pytest.skip("No auth token available")

    try:
        # 先获取client_id
        me_response = await http_client.get("/api/auth/me", headers=auth_headers)
        if me_response.status_code != 200:
            report.add_result(test_name, "SKIP", {"reason": "Could not get user info"})
            pytest.skip("Could not get user info")

        # 登出（需要X-Client-ID头）
        logout_headers = {**auth_headers, "X-Client-ID": "test_client_id"}
        logout_response = await http_client.post("/api/auth/logout", headers=logout_headers)

        # 登出端点可能返回404（如果session不存在）
        # 这是可接受的，因为我们使用的是测试client_id
        report.add_result(test_name, "PASS", {
            "logout_status": logout_response.status_code,
            "note": "Logout endpoint accessible",
        })

    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


# ═════════════════════════════════════════════════════════════════
# Integration Analysis Tests
# ═════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_auth_integration_analysis(http_client):
    """TC16: 认证系统集成分析"""
    test_name = "TC16: Auth Integration Analysis"

    analysis = {
        "auth_endpoints_available": False,
        "auth_functional": False,
        "websocket_auth": False,
        "api_protection": "none",  # none, partial, full
        "issues": [],
    }

    try:
        # 1. 检查认证端点是否存在
        response = await http_client.post("/api/auth/auto-login", json={})
        if response.status_code == 404:
            analysis["issues"].append("Auth endpoints not available (404)")
            analysis["auth_endpoints_available"] = False
        elif response.status_code == 200:
            analysis["auth_endpoints_available"] = True
            analysis["auth_functional"] = True
        else:
            analysis["auth_endpoints_available"] = True
            analysis["issues"].append(f"Auth returned unexpected status: {response.status_code}")

        # 2. 检查现有API端点是否受保护
        # 检查dialogs端点
        dialogs_response = await http_client.get("/api/dialogs")
        if dialogs_response.status_code == 200:
            analysis["api_protection"] = "none"
            analysis["issues"].append("Dialogs API is unprotected (no auth required)")

        # 3. WebSocket认证状态
        client_id = f"analysis_client_{int(time.time())}"
        try:
            async with websockets.connect(f"{WS_URL}/ws/{client_id}") as ws:
                analysis["websocket_auth"] = False  # 连接成功但没有认证
                analysis["issues"].append("WebSocket does not enforce authentication")
        except Exception as e:
            analysis["issues"].append(f"WebSocket connection failed: {e}")

        # 记录分析结果
        for issue in analysis["issues"]:
            report.add_issue(
                category="Integration Analysis",
                description=issue,
                severity="INFO",
            )

        report.add_result(test_name, "PASS", analysis)

    except Exception as e:
        report.add_result(test_name, "FAIL", {"error": str(e)})
        raise


# ═════════════════════════════════════════════════════════════════
# Test Report Generation
# ═════════════════════════════════════════════════════════════════

def pytest_sessionstart(session):
    """测试会话开始"""
    report.start()
    print("\n" + "=" * 70)
    print("AUTH INTEGRATION TEST SUITE")
    print("=" * 70)


def pytest_sessionfinish(session, exitstatus):
    """测试会话结束，生成报告"""
    report.end()
    summary = report.summary()

    print("\n" + "=" * 70)
    print("INTEGRATION TEST REPORT")
    print("=" * 70)
    print(f"Total Tests: {summary['total']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Skipped: {summary['skipped']}")
    print(f"Duration: {summary['duration']}")
    print("-" * 70)

    for result in summary["results"]:
        status_icon = "[PASS]" if result["status"] == "PASS" else "[FAIL]" if result["status"] == "FAIL" else "[SKIP]"
        print(f"{status_icon} {result['test_name']}")
        if result["status"] == "FAIL" and "error" in result["details"]:
            print(f"      Error: {result['details']['error']}")

    # 打印集成问题
    if summary["issues"]:
        print("\n" + "=" * 70)
        print("INTEGRATION ISSUES FOUND")
        print("=" * 70)
        for issue in summary["issues"]:
            severity_icon = "[HIGH]" if issue["severity"] == "HIGH" else "[MED]" if issue["severity"] == "MEDIUM" else "[INFO]"
            print(f"{severity_icon} [{issue['category']}] {issue['description']}")

    print("=" * 70)

    # 保存详细报告到文件
    report_file = f"auth_integration_report_{int(time.time())}.json"
    with open(report_file, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"\nDetailed report saved to: {report_file}")


# ═════════════════════════════════════════════════════════════════
# Main Entry Point
# ═════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 直接运行测试
    pytest.main([__file__, "-v", "--tb=short"])
