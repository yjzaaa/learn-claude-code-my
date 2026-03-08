"""
测试 BaseAgentLoop - 打印全流程 messages 并保存为 JSONL

用法:
    python test_base_agent_loop.py
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable
import re
# 设置环境变量（如果需要）
from dotenv import load_dotenv
from pydantic_core import to_json
load_dotenv(override=True)
from agents.base import BaseAgentLoop, WorkspaceOps, tool, build_tools_and_handlers


def test_base_agent_loop():
    """测试 BaseAgentLoop 并记录所有 messages"""

    import os
    model = os.getenv("MODEL_ID", "deepseek-reasoner")
    dialog_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 用于存储所有消息的列表
    all_messages_log = []
    def on_tool_call(token, block):
        """工具调用时记录"""
        print(f"\n[Tool Call] {token}")

    def on_stream_token(token):
        """流式 token（如果需要）"""
        print(f"[Stream Token] {token}")
        pass  # 流式 token 太多，不打印


    def on_stop():
    
        # 保存完整消息到 all_messages_log
        all_messages_log.extend(messages)
    


    @tool(name="get_current_time", description="Get the current time")  
    def get_current_time():
        return datetime.now().isoformat()
    
    @tool(name="calculate", description="Perform a calculation")
    def calculate(expression: str) -> str:
        """Perform a calculation"""
        try:
            return str(eval(expression))
        except Exception as e:
            return f"Error: {str(e)}"
        

    tools, handlers = build_tools_and_handlers([get_current_time, calculate])
    # 创建 BaseAgentLoop 实例
    loop = BaseAgentLoop(
        model=model,
        system="You are a helpful assistant. Use tools when needed.",
        tools=tools,
        tool_handlers=handlers,
        max_tokens=1000,
        max_rounds=10,
        on_tool_call=on_tool_call,
        on_stream_token=on_stream_token,
        on_stop=on_stop,
    )

    # 测试问题 - 需要工具调用
    user_question = "What is the current time? And calculate 123 * 456 for me."



    # 初始消息
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when needed."},
        {"role": "user", "content": user_question}
    ]

    loop.run(messages)
    # 保存到 JSONL 文件
    output_dir = Path(".logs")
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / f"{dialog_id}_messages.jsonl"

    # 保存消息和 usage 到 JSONL
    with open(output_file, "w", encoding="utf-8") as f:
        # 写入消息
        for msg in messages:
            f.write(json.dumps(msg, ensure_ascii=False, default=str) + "\n")

    print(f"\n{'#'*60}")
    print(f"# Messages saved to: {output_file}")
    print(f"# Total messages: {len(messages)}")
    print(f"{'#'*60}\n")

    # 打印完整消息结构
    print("\n" + "="*60)
    print("FULL MESSAGE LOG")
    print("="*60)
    for i, msg in enumerate(messages):
        print(f"\n--- Message {i} ---")
        print(json.dumps(msg, indent=2, ensure_ascii=False, default=str))

    return messages


if __name__ == "__main__":
    test_base_agent_loop()
