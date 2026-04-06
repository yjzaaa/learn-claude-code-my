#!/usr/bin/env python3
"""
Playwright CLI 流式输出测试

使用方法:
  python playwright_stream_test.py --headed  # 有界面模式
  python playwright_stream_test.py           # 无界面模式
"""

import argparse
import asyncio
import io
import json
import os
import sys

# 设置 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


async def test_streaming_output(headed: bool = False):
    """测试流式输出"""
    from playwright.async_api import async_playwright

    results = {
        "success": False,
        "chunks": [],
        "messages": [],
        "errors": []
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed, slow_mo=50)
        context = await browser.new_context()
        page = await context.new_page()

        # 捕获 WebSocket 消息
        ws_messages = []

        def handle_ws(ws):
            print(f"[WebSocket] 连接: {ws.url}")

            async def on_message(msg):
                try:
                    data = json.loads(msg)
                    ws_messages.append(data)
                    msg_type = data.get('type', 'unknown')
                    print(f"[WebSocket] 收到: {msg_type}")

                    # 记录流式输出事件
                    if msg_type in ['stream:delta', 'text_delta', 'delta']:
                        results["chunks"].append({
                            "type": msg_type,
                            "timestamp": data.get('timestamp'),
                            "content_length": len(str(data.get('content', '')))
                        })
                except:
                    pass

            ws.on("framereceived", lambda msg: asyncio.create_task(on_message(msg)))

        page.on("websocket", handle_ws)

        try:
            # 1. 打开页面
            print("\n[1/4] 打开聊天页面...")
            await page.goto("http://localhost:3000/en/chat", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)
            print("  [OK] 页面加载完成")

            # 2. 创建新对话
            print("\n[2/4] 创建新对话...")
            new_chat_btn = await page.wait_for_selector("[title='新建对话']", timeout=5000)
            await new_chat_btn.click()
            await page.wait_for_timeout(2000)
            print("  [OK] 新对话已创建")

            # 3. 发送测试消息
            print("\n[3/4] 发送测试消息...")
            test_message = "执行 finance skill 体温测试"

            # 找到输入框并输入
            input_elem = await page.wait_for_selector("textarea", timeout=5000)
            await input_elem.fill(test_message)
            print(f"  [OK] 输入消息: {test_message}")

            # 按 Enter 发送
            await input_elem.press("Enter")
            print("  [OK] 消息已发送")

            # 4. 监控流式输出
            print("\n[4/4] 监控流式输出...")
            print("  等待 WebSocket 消息...")

            # 等待一段时间收集消息
            await asyncio.sleep(10)

            # 分析结果
            results["ws_message_count"] = len(ws_messages)
            results["streaming_events"] = len([m for m in ws_messages
                                                if m.get('type') in ['stream:delta', 'text_delta', 'delta']])

            print(f"\n  [统计] WebSocket 消息总数: {results['ws_message_count']}")
            print(f"  [统计] 流式输出事件数: {results['streaming_events']}")

            # 列出所有消息类型
            msg_types = {}
            for m in ws_messages:
                t = m.get('type', 'unknown')
                msg_types[t] = msg_types.get(t, 0) + 1

            print("\n  [消息类型分布]:")
            for t, count in msg_types.items():
                print(f"    - {t}: {count}")

            # 判断是否成功
            results["success"] = results["ws_message_count"] > 0
            results["streaming_working"] = results["streaming_events"] > 0

        except Exception as e:
            results["errors"].append(str(e))
            print(f"\n  [ERROR] 测试失败: {e}")

        finally:
            await context.close()
            await browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(description="前端流式输出测试")
    parser.add_argument("--headed", action="store_true", help="显示浏览器界面")
    args = parser.parse_args()

    print("="*60)
    print("Playwright CLI - 前端流式输出测试")
    print("="*60)

    results = asyncio.run(test_streaming_output(headed=args.headed))

    # 输出报告
    print("\n" + "="*60)
    print("测试报告")
    print("="*60)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # 结果判断
    if results["success"]:
        print("\n[PASS] 测试通过!")
        if results["streaming_working"]:
            print("[PASS] 流式输出正常工作")
        else:
            print("[WARN] 未检测到流式输出事件")
        return 0
    print("\n[FAIL] 测试失败")
    return 1


if __name__ == "__main__":
    sys.exit(main())
