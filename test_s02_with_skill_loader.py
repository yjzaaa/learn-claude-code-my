"""测试 s02_with_skill_loader 的钩子捕获能力（真实 provider）。

用法:
    python test_s02_with_skill_loader.py

说明:
- 使用真实 create_provider_from_env() 提供的模型调用
- 验证 on_stream_token / on_tool_call / on_complete / on_error 的捕获行为
- 运行后会将消息与钩子统计写入 .logs
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from agents.agent.s02_with_skill_loader import S02WithSkillLoaderAgent
from agents.base.abstract import FullAgentHooks


class CaptureHooks(FullAgentHooks):
    """Hook collector constrained by the full hook interface."""

    def __init__(self, hook_stats: dict[str, Any]) -> None:
        self.hook_stats = hook_stats

    def on_before_run(self, messages: list[dict[str, Any]]) -> None:
        _ = messages

    def on_stream_token(self, chunk: Any) -> None:
        print(f"[Stream Token] {str(chunk)[:100]}...")  # 仅打印前100字符，避免过长输出
        self.hook_stats["stream_total"] += 1
        if getattr(chunk, "is_content", False):
            self.hook_stats["content_chunks"] += 1
        if getattr(chunk, "is_reasoning", False):
            self.hook_stats["reasoning_chunks"] += 1
        if getattr(chunk, "is_tool_call", False):
            self.hook_stats["tool_chunks"] += 1
        if getattr(chunk, "is_done", False):
            self.hook_stats["done_chunks"] += 1
        if getattr(chunk, "is_error", False):
            self.hook_stats["error_chunks"] += 1

    def on_tool_call(self, name: str, arguments: dict[str, Any]) -> None:
        self.hook_stats["tool_calls"].append({"name": name, "arguments": arguments})

    def on_tool_result(
        self,
        name: str,
        result: str,
        assistant_message: dict[str, Any] | None = None,
        tool_call_id: str = "",
    ) -> None:
        _ = (name, result)
        self.hook_stats["tool_results"].append(
            {
                "name": name,
                "tool_call_id": tool_call_id,
                "assistant_has_tool_calls": bool((assistant_message or {}).get("tool_calls")),
            }
        )

    def on_complete(self, content: str) -> None:
        self.hook_stats["complete_payload"] = content

    def on_error(self, error: Exception) -> None:
        self.hook_stats["errors"].append(str(error))

    def on_after_run(self, messages: list[dict[str, Any]], rounds: int) -> None:
        _ = messages
        self.hook_stats["after_run_rounds"] = rounds

    def on_stop(self) -> None:
        return None


def test_s02_with_skill_loader_hooks_real_provider() -> dict[str, Any]:
    """真实 provider 下测试钩子是否覆盖主要过程。"""

    print("=" * 60)
    print("Testing s02_with_skill_loader hooks with REAL provider")
    print("=" * 60)

    hook_stats: dict[str, Any] = {
        "stream_total": 0,
        "content_chunks": 0,
        "reasoning_chunks": 0,
        "tool_chunks": 0,
        "done_chunks": 0,
        "error_chunks": 0,
        "tool_calls": [],
        "tool_results": [],
        "complete_payload": "",
        "errors": [],
        "after_run_rounds": 0,
    }

    agent = S02WithSkillLoaderAgent()
    agent.set_hook_delegate(CaptureHooks(hook_stats))
    if agent.provider is None:
        raise RuntimeError("No provider from env. Please configure .env before running this test.")

    agent.max_rounds = 25

    messages = [
        {
            "role": "user",
            "content": (
                "请严格先调用 load_skill 工具，name=finance；"
                "26财年计划了多少HR费用的预算？"
            ),
        }
    ]

    result = agent.run(messages)

    # 关键断言：钩子必须捕获到主流程。
    assert hook_stats["stream_total"] > 0, "on_stream_token did not capture any chunk"
    assert hook_stats["done_chunks"] > 0, "on_stream_token did not capture completion chunk"
    assert len(hook_stats["errors"]) == 0, f"on_error captured errors: {hook_stats['errors']}"
    assert hook_stats["complete_payload"] != "", "on_complete did not capture final payload"
    assert len(hook_stats["tool_calls"]) > 0, "on_tool_call did not capture tool invocation"
    assert hook_stats["after_run_rounds"] > 0, "on_after_run did not capture executed rounds"

    # 写入日志快照，便于回溯。
    log_dir = Path(".logs")
    log_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = log_dir / f"s02_with_skill_loader_hooks_{stamp}.json"
    out_path.write_text(
        json.dumps(
            {
                "result": result,
                "hook_stats": hook_stats,
                "messages": messages,
            },
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print("[OK] Hooks captured full process")
    print(f"[OK] Stream chunks: {hook_stats['stream_total']}")
    print(f"[OK] Tool calls captured: {len(hook_stats['tool_calls'])}")
    print(f"[OK] Log saved: {out_path}")

    return {"result": result, "hook_stats": hook_stats, "log": str(out_path)}


if __name__ == "__main__":
    test_s02_with_skill_loader_hooks_real_provider()
    print("[PASS] test_s02_with_skill_loader_hooks_real_provider")
