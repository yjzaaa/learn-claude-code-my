#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playwright CLI 流式输出测试

使用方法:
  python playwright_cli_test.py --headed  # 有界面模式
  python playwright_cli_test.py           # 无界面模式
"""

import argparse
import asyncio
import json
import sys
import os
import io

# 设置 UTF-8 编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from pathlib import Path

# 添加项目根目录
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def check_dependencies():
    """检查依赖是否安装"""
    try:
        from playwright.async_api import async_playwright
        return True
    except ImportError:
        print("错误: 请先安装 playwright")
        print("  pip install playwright")
        print("  playwright install chromium")
        return False


async def run_stream_test(headed: bool = False, slow_mo: int = 100):
    """运行流式输出测试"""
    from playwright.async_api import async_playwright

    results = {
        "success": False,
        "chunks": [],
        "errors": []
    }

    async with async_playwright() as p:
        # 启动浏览器
        browser = await p.chromium.launch(
            headless=not headed,
            slow_mo=slow_mo
        )

        context = await browser.new_context()
        page = await context.new_page()

        # 收集 console 日志
        page.on("console", lambda msg: print(f"[Console] {msg.type}: {msg.text}"))

        try:
            # 1. 打开聊天页面
            print("\n[1/4] 打开聊天页面...")
            await page.goto("http://localhost:3000/en/chat", wait_until="domcontentloaded")
            await page.wait_for_timeout(3000)  # 等待 React 渲染
            print("  [OK] 页面加载完成")

            # 1.5 创建新对话
            print("\n[1.5] 创建新对话...")
            try:
                new_chat_btn = await page.wait_for_selector("[title='新建对话']", timeout=5000)
                await new_chat_btn.click()
                print("  [OK] 点击新建对话按钮")
                await page.wait_for_timeout(2000)  # 等待对话创建
            except Exception as e:
                print(f"  [WARN] 创建对话失败: {e}")

            # 2. 查找输入框并输入消息
            print("\n[2/4] 发送测试消息...")

            # 尝试多种选择器 (匹配 InputArea.tsx)
            input_selectors = [
                "textarea[placeholder*='发消息']",
                "textarea[placeholder*='message']",
                "textarea"
            ]

            input_elem = None
            for selector in input_selectors:
                try:
                    input_elem = await page.wait_for_selector(selector, timeout=2000)
                    if input_elem:
                        print(f"  找到输入框: {selector}")
                        break
                except Exception as e:
                    print(f"  [调试] {selector} 失败: {e}")
                    continue

            # 调试: 打印所有 textarea
            if not input_elem:
                print("  [调试] 查找所有 textarea...")
                all_ta = await page.query_selector_all("textarea")
                print(f"  [调试] 找到 {len(all_ta)} 个 textarea")
                for i, ta in enumerate(all_ta[:3]):
                    ph = await ta.get_attribute("placeholder") or "(无)"
                    print(f"    [{i}] placeholder='{ph}'")

            if not input_elem:
                raise Exception("未找到输入框")

            # 输入消息
            test_message = "执行 finance skill 体温测试"
            await input_elem.fill(test_message)
            print(f"  输入消息: {test_message}")

            # 3. 查找发送按钮并点击
            print("\n[3/4] 点击发送按钮...")

            send_selectors = [
                "button[type='submit']",
                "button:has-text('Send')",
                "button:has(svg)",
                "button[aria-label*='send']",
                "button"
            ]

            send_btn = None
            for selector in send_selectors:
                try:
                    send_btn = await page.wait_for_selector(selector, timeout=1000)
                    if send_btn:
                        print(f"  找到发送按钮: {selector}")
                        break
                except:
                    continue

            if not send_btn:
                # 尝试按 Enter 键
                print("  尝试按 Enter 键发送...")
                await input_elem.press("Enter")
            else:
                try:
                    await send_btn.click(timeout=5000)
                    print("  [OK] 点击发送按钮")
                except:
                    # 如果点击失败，使用 Enter 键
                    print("  点击失败，使用 Enter 键...")
                    await input_elem.press("Enter")

            # 4. 监控流式输出
            print("\n[4/4] 监控流式输出...")

            start_time = asyncio.get_event_loop().time()
            chunks_count = 0
            last_content = ""
            max_wait = 30  # 最大等待30秒

            while (asyncio.get_event_loop().time() - start_time) < max_wait:
                # 查找 AI 回复
                message_selectors = [
                    "text=Hana >> xpath=following-sibling::div",  # Hana 标签旁边的 div
                    "span:has-text('Hana') + div",
                    "[data-role='assistant']",
                    ".message-assistant",
                ]

                current_content = ""
                for selector in message_selectors:
                    try:
                        elems = await page.query_selector_all(selector)
                        if elems:
                            last_elem = elems[-1]
                            current_content = await last_elem.inner_text()
                            break
                    except:
                        continue

                # 调试: 如果第一次没有内容，打印页面信息
                if not current_content and chunks_count == 0:
                    try:
                        # 尝试直接获取页面上的所有文本
                        body_text = await page.evaluate('() => document.body.innerText')
                        if 'Hana' in body_text:
                            print(f"  [调试] 页面包含 'Hana'，但选择器未匹配")
                            # 尝试查找包含 Hana 的元素
                            hana_divs = await page.query_selector_all('div:has-text("Hana")')
                            print(f"  [调试] 找到 {len(hana_divs)} 个包含 Hana 的 div")
                    except Exception as e:
                        pass

                if current_content and current_content != last_content:
                    chunks_count += 1
                    new_text = current_content[len(last_content):]
                    results["chunks"].append({
                        "index": chunks_count,
                        "text": new_text[:50],  # 只记录前50字符
                        "timestamp": asyncio.get_event_loop().time() - start_time
                    })
                    print(f"  [Chunk #{chunks_count}] {new_text[:30]}...")
                    last_content = current_content

                # 检查是否完成
                await asyncio.sleep(0.5)

                # 如果 2 秒没有新内容，认为完成
                if chunks_count > 0:
                    await asyncio.sleep(2)
                    check_content = ""
                    for selector in message_selectors:
                        try:
                            elems = await page.query_selector_all(selector)
                            if elems:
                                check_content = await elems[-1].inner_text()
                                break
                        except:
                            continue
                    if check_content == last_content:
                        print("  [OK] 输出完成")
                        break

            # 汇总结果
            duration = asyncio.get_event_loop().time() - start_time
            results.update({
                "success": chunks_count > 0,
                "total_chunks": chunks_count,
                "duration": duration,
                "streaming_working": chunks_count > 1,
                "final_content_length": len(last_content)
            })

        except Exception as e:
            results["errors"].append(str(e))
            print(f"\n  [ERROR] 错误: {e}")

        finally:
            await context.close()
            await browser.close()

    return results


def main():
    parser = argparse.ArgumentParser(description="Finance Skill 流式输出测试")
    parser.add_argument("--headed", action="store_true", help="显示浏览器界面")
    parser.add_argument("--slow-mo", type=int, default=100, help="操作延迟(ms)")
    args = parser.parse_args()

    print("=" * 60)
    print("Playwright CLI - Finance Skill 流式输出测试")
    print("=" * 60)

    if not check_dependencies():
        return 1

    # 运行测试
    results = asyncio.run(run_stream_test(headed=args.headed, slow_mo=args.slow_mo))

    # 输出报告
    print("\n" + "=" * 60)
    print("测试报告")
    print("=" * 60)
    print(json.dumps(results, indent=2, ensure_ascii=False))

    # 判断结果
    if results["success"]:
        print("\n[PASS] 测试通过!")
        if results["streaming_working"]:
            print("[PASS] 流式输出正常工作 (检测到多 chunks)")
        else:
            print("[WARN] 只有单块输出，可能不是流式")
        return 0
    else:
        print("\n[FAIL] 测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
