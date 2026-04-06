"""
Playwright E2E 测试 - 前端流式输出验证

测试场景：
1. 打开前端聊天页面
2. 发送消息
3. 验证流式输出（token 逐字显示）
4. 检查 WebSocket 连接
"""

import asyncio
import json
from typing import Any

from playwright.async_api import BrowserContext, Page, async_playwright


class ChatStreamTester:
    """聊天流式输出测试器"""

    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.page: Page = None
        self.context: BrowserContext = None
        self.browser = None
        self.received_chunks: list[str] = []
        self.ws_messages: list[dict] = []

    async def setup(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # 监听 WebSocket 消息
        self.page.on("websocket", self._handle_ws)

    async def teardown(self):
        """清理资源"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    def _handle_ws(self, ws):
        """处理 WebSocket 事件"""
        print(f"[WebSocket] 连接: {ws.url}")

        ws.on("framesent", lambda payload: self._log_ws_message("sent", payload))
        ws.on("framereceived", lambda payload: self._log_ws_message("received", payload))

    def _log_ws_message(self, direction: str, payload):
        """记录 WebSocket 消息"""
        try:
            if isinstance(payload, str):
                data = json.loads(payload)
                self.ws_messages.append({
                    "direction": direction,
                    "data": data,
                    "timestamp": asyncio.get_event_loop().time()
                })
                print(f"[WebSocket {direction}] {data.get('type', 'unknown')}")
        except:
            pass

    async def navigate_to_chat(self):
        """导航到聊天页面"""
        chat_url = f"{self.base_url}/en/chat"
        print(f"[导航] 打开页面: {chat_url}")
        await self.page.goto(chat_url, wait_until="networkidle")
        await self.page.wait_for_load_state("domcontentloaded")

        # 等待页面初始化
        await asyncio.sleep(2)

    async def send_message(self, message: str) -> bool:
        """发送消息并返回是否成功"""
        try:
            # 查找输入框
            input_selector = "textarea[placeholder*='message'], textarea[placeholder*='Message'], input[type='text']"
            await self.page.wait_for_selector(input_selector, timeout=5000)

            # 输入消息
            print(f"[发送] 输入消息: {message}")
            await self.page.fill(input_selector, message)

            # 查找发送按钮
            send_button = "button[type='submit'], button:has-text('Send'), button:has(svg)"
            await self.page.click(send_button)

            return True
        except Exception as e:
            print(f"[错误] 发送消息失败: {e}")
            return False

    async def wait_for_streaming(self, timeout: int = 30) -> dict[str, Any]:
        """等待流式输出完成"""
        start_time = asyncio.get_event_loop().time()
        chunks = []
        last_content = ""

        print("[等待] 等待流式输出...")

        while (asyncio.get_event_loop().time() - start_time) < timeout:
            # 获取当前显示的消息内容
            try:
                # 查找 AI 消息气泡
                message_selector = "[data-role='assistant'], .message-assistant, .ai-message"
                elements = await self.page.query_selector_all(message_selector)

                if elements:
                    # 获取最后一个 AI 消息的内容
                    last_element = elements[-1]
                    current_content = await last_element.inner_text()

                    if current_content != last_content:
                        # 检测到新内容
                        new_chunk = current_content[len(last_content):]
                        if new_chunk:
                            chunks.append({
                                "text": new_chunk,
                                "timestamp": asyncio.get_event_loop().time() - start_time,
                                "total_length": len(current_content)
                            })
                            print(f"[Chunk #{len(chunks)}] {new_chunk[:50]}...")
                            last_content = current_content

                    # 检查是否完成（没有新的 delta 事件）
                    if len(chunks) > 0:
                        await asyncio.sleep(1)
                        new_content = await last_element.inner_text()
                        if new_content == last_content:
                            print("[完成] 流式输出结束")
                            break

            except Exception as e:
                print(f"[警告] 获取内容时出错: {e}")

            await asyncio.sleep(0.5)

        return {
            "chunks": chunks,
            "total_chunks": len(chunks),
            "final_content": last_content,
            "duration": asyncio.get_event_loop().time() - start_time,
            "ws_messages": len(self.ws_messages)
        }

    async def test_finance_skill_health(self) -> dict[str, Any]:
        """测试 Finance Skill 体温检查"""
        print("\n" + "="*60)
        print("开始 Finance Skill 流式输出测试")
        print("="*60)

        # 1. 导航到聊天页面
        await self.navigate_to_chat()

        # 2. 发送体温测试命令
        test_message = "/skill finance health"
        success = await self.send_message(test_message)
        if not success:
            return {"success": False, "error": "发送消息失败"}

        # 3. 等待流式输出
        result = await self.wait_for_streaming(timeout=30)

        # 4. 分析结果
        analysis = {
            "success": result["total_chunks"] > 0,
            "streaming_working": result["total_chunks"] > 1,
            "chunks_count": result["total_chunks"],
            "duration": result["duration"],
            "final_content_length": len(result["final_content"]),
            "ws_messages_count": result["ws_messages"],
            "chunks_detail": result["chunks"][:5]  # 只显示前5个 chunk
        }

        print("\n" + "="*60)
        print("测试结果")
        print("="*60)
        for key, value in analysis.items():
            print(f"  {key}: {value}")

        return analysis


async def run_test():
    """运行测试"""
    tester = ChatStreamTester(base_url="http://localhost:3000")

    try:
        await tester.setup()
        result = await tester.test_finance_skill_health()

        if result["success"]:
            print("\n✅ 测试通过: 流式输出正常工作")
            if result["streaming_working"]:
                print("✅ 检测到 Token 级流式输出")
            else:
                print("⚠️  只有单个输出块，可能不是流式")
        else:
            print(f"\n❌ 测试失败: {result.get('error', '未知错误')}")

        return result

    finally:
        await tester.teardown()


if __name__ == "__main__":
    result = asyncio.run(run_test())
    print("\n最终报告:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
