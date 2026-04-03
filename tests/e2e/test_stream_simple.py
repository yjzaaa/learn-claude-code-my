"""
简化版流式输出测试 - 使用 websockets 直接测试后端
"""

import asyncio
import json
import websockets
import aiohttp
from typing import List, Dict, Any
import time


async def test_chat_streaming(
    base_url: str = "ws://localhost:8001",
    message: str = "执行 finance skill 体温测试"
) -> Dict[str, Any]:
    """
    测试聊天流式输出

    流程：
    1. 创建对话
    2. 通过 WebSocket 发送消息
    3. 接收流式响应
    4. 统计 chunk 数量和延迟
    """

    chunks: List[Dict] = []
    start_time = time.time()

    print(f"[测试] 连接到 {base_url}/ws/chat")

    try:
        async with websockets.connect(f"{base_url}/ws/chat") as ws:
            print("[WebSocket] 连接成功")

            # 创建新对话
            create_msg = {
                "action": "create_dialog",
                "content": message,
                "title": "Finance Skill 体温测试"
            }
            await ws.send(json.dumps(create_msg))

            # 接收创建响应
            response = await ws.recv()
            data = json.loads(response)
            dialog_id = data.get("dialog_id", "test-dialog")
            print(f"[对话] 创建成功: {dialog_id}")

            # 发送消息
            send_msg = {
                "action": "send_message",
                "dialog_id": dialog_id,
                "content": message,
                "stream": True
            }
            await ws.send(json.dumps(send_msg))
            print(f"[发送] 消息: {message}")

            # 接收流式响应
            print("[接收] 等待流式输出...")
            chunk_count = 0

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                    data = json.loads(msg)

                    chunk_count += 1
                    chunk_info = {
                        "index": chunk_count,
                        "type": data.get("type", "unknown"),
                        "timestamp": time.time() - start_time,
                        "data_preview": str(data)[:100]
                    }
                    chunks.append(chunk_info)

                    # 打印进度
                    if chunk_count <= 10 or chunk_count % 10 == 0:
                        print(f"  [Chunk #{chunk_count}] {data.get('type', 'unknown')} "
                              f"({chunk_info['timestamp']:.2f}s)")

                    # 检查是否完成
                    if data.get("type") == "complete" or data.get("done"):
                        print(f"[完成] 收到完成信号")
                        break

                except asyncio.TimeoutError:
                    print("[超时] 30秒内没有收到消息")
                    break

            duration = time.time() - start_time

            return {
                "success": True,
                "dialog_id": dialog_id,
                "total_chunks": chunk_count,
                "duration": duration,
                "chunks_per_second": chunk_count / duration if duration > 0 else 0,
                "first_chunk_latency": chunks[0]["timestamp"] if chunks else 0,
                "streaming_working": chunk_count > 1,
                "sample_chunks": chunks[:5]
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total_chunks": len(chunks),
            "duration": time.time() - start_time
        }


async def main():
    """主函数"""
    print("="*60)
    print("Finance Skill 流式输出测试")
    print("="*60)

    # 测试 1: 普通对话
    print("\n[测试 1] 发送普通消息...")
    result1 = await test_chat_streaming(
        message="执行 finance skill 体温测试"
    )

    print("\n" + "="*60)
    print("测试结果")
    print("="*60)
    print(f"  成功: {result1['success']}")
    print(f"  Chunk 数量: {result1.get('total_chunks', 0)}")
    print(f"  总耗时: {result1.get('duration', 0):.2f}s")
    print(f"  流式输出: {'是' if result1.get('streaming_working') else '否'}")

    if result1.get('sample_chunks'):
        print("\n  前 3 个 chunks:")
        for chunk in result1['sample_chunks'][:3]:
            print(f"    #{chunk['index']}: {chunk['type']} @ {chunk['timestamp']:.3f}s")

    # 保存详细报告
    report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "results": {
            "health_check": result1
        }
    }

    with open("test_stream_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[报告] 已保存到 test_stream_report.json")

    return result1


if __name__ == "__main__":
    result = asyncio.run(main())

    if result.get("success") and result.get("streaming_working"):
        print("\n✅ 测试通过: 流式输出正常工作")
        exit(0)
    else:
        print("\n❌ 测试失败")
        exit(1)
