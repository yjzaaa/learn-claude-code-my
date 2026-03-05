#!/usr/bin/env python3
"""
s06_context_compact.py - 上下文压缩

三层压缩流水线，让代理在长会话中持续工作：

    每一轮：
    +------------------+
    | Tool call result |
    +------------------+
            |
            v
        [第 1 层: micro_compact]        （每轮静默执行）
            将除最近 3 条以外的 tool_result 内容替换为
            "[Previous: used {tool_name}]"
            |
            v
    [检查：tokens > 50000 ?]
       |               |
       no              yes
       |               |
       v               v
    continue    [第 2 层: auto_compact]
                  保存完整对话到 .transcripts/
                  让 LLM 生成会话摘要
                  用摘要替换当前 messages
                        |
                        v
                                [第 3 层: compact 工具]
                                    模型调用 compact 后立即压缩
                                    逻辑与 auto 相同，仅手动触发

关键点："通过策略性遗忘，代理可以长期稳定运行。"
"""

import json
import os
import time
from pathlib import Path

from client import get_client, get_model
from dotenv import load_dotenv
try:
    from base import BaseAgentLoop, WorkspaceOps, tool
except ImportError:
    from agents.base import BaseAgentLoop, WorkspaceOps, tool

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
client = get_client()
MODEL = get_model()
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"You are a coding agent at {WORKDIR}. Use tools to solve tasks."

THRESHOLD = 50000
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
KEEP_RECENT = 3


def estimate_tokens(messages: list) -> int:
    """粗略估算 token 数：约 4 个字符约等于 1 个 token。"""
    return len(str(messages)) // 4


# -- 第 1 层：micro_compact，将旧 tool_result 替换为占位符 --
def micro_compact(messages: list) -> list:
    # 收集所有 tool_result 的位置与内容
    tool_results = []
    for msg_idx, msg in enumerate(messages):
        if msg["role"] == "user" and isinstance(msg.get("content"), list):
            for part_idx, part in enumerate(msg["content"]):
                if isinstance(part, dict) and part.get("type") == "tool_result":
                    tool_results.append((msg_idx, part_idx, part))
    if len(tool_results) <= KEEP_RECENT:
        return messages
    # 通过 tool_use_id 回溯对应的工具名
    tool_name_map = {}
    for msg in messages:
        if msg["role"] == "assistant":
            content = msg.get("content", [])
            if isinstance(content, list):
                for block in content:
                    if hasattr(block, "type") and block.type == "tool_use":
                        tool_name_map[block.id] = block.name
    # 清理旧结果（仅保留最近 KEEP_RECENT 条完整内容）
    to_clear = tool_results[:-KEEP_RECENT]
    for _, _, result in to_clear:
        if isinstance(result.get("content"), str) and len(result["content"]) > 100:
            tool_id = result.get("tool_use_id", "")
            tool_name = tool_name_map.get(tool_id, "unknown")
            result["content"] = f"[Previous: used {tool_name}]"
    return messages


# -- 第 2 层：auto_compact，落盘全文后生成摘要并替换消息 --
def auto_compact(messages: list) -> list:
    # 将完整对话写入磁盘
    TRANSCRIPT_DIR.mkdir(exist_ok=True)
    transcript_path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with open(transcript_path, "w") as f:
        for msg in messages:
            f.write(json.dumps(msg, default=str) + "\n")
    print(f"[transcript saved: {transcript_path}]")
    # 请求模型生成连续性摘要
    conversation_text = json.dumps(messages, default=str)[:80000]
    response = client.messages.create(
        model=MODEL,
        messages=[{"role": "user", "content":
            "Summarize this conversation for continuity. Include: "
            "1) What was accomplished, 2) Current state, 3) Key decisions made. "
            "Be concise but preserve critical details.\n\n" + conversation_text}],
        max_tokens=2000,
    )
    summary = response.content[0].text
    # 用压缩后的摘要替换当前上下文
    return [
        {"role": "user", "content": f"[Conversation compressed. Transcript: {transcript_path}]\n\n{summary}"},
        {"role": "assistant", "content": "Understood. I have the context from the summary. Continuing."},
    ]

@tool(name="compact", description="Trigger manual conversation compression.")
def compact(focus: str | None = None) -> str:
    _ = focus
    return "Compressing..."


TOOLS = OPS.get_tools() + [compact]

_S06_STATE = {"manual_compact": False}


def _on_before_round(messages: list):
    # 第 1 层：每次模型调用前先做微压缩
    micro_compact(messages)
    # 第 2 层：超阈值时自动压缩
    if estimate_tokens(messages) > THRESHOLD:
        print("[auto_compact triggered]")
        messages[:] = auto_compact(messages)


def _on_tool_result(block, output: str, results: list, messages: list):
    print(f"> {block.name}: {output[:200]}")
    if block.name == "compact":
        _S06_STATE["manual_compact"] = True


def _on_after_round(messages: list, response):
    # 第 3 层：由 compact 工具触发手动压缩
    if _S06_STATE["manual_compact"]:
        print("[manual compact]")
        messages[:] = auto_compact(messages)
        _S06_STATE["manual_compact"] = False


AGENT_LOOP = BaseAgentLoop(
    client=client,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
    on_before_round=_on_before_round,
    on_tool_result=_on_tool_result,
    on_after_round=_on_after_round,
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms06 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    print(block.text)
        print()


