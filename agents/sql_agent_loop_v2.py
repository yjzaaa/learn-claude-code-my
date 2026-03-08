"""
SQL Agent Loop V2 - 主-子代理架构 with 自动问题总结与学习优化

核心设计理念 (参考 s04_subagent.py):
1. 主代理(Master)专注决策与规划
2. 子代理(Worker)专注执行，有独立上下文 (fresh messages=[])
3. 子代理只返回摘要给主代理，上下文结束后丢弃
4. 记忆系统(LearningMemory)持久化成功/失败模式

架构图:
┌─────────────────────────────────────────────────────────────────┐
│                        Master Agent                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  Task Planner│  │ Result Merge │  │ Learning Integrator  │   │
│  └──────────────┘  └──────────────┘  └──────────────────────┘   │
└──────────┬──────────────────────────────────────────────────────┘
           │ delegate (prompt)       │ summary
           ▼                         ▼
┌────────────────────┐      ┌────────────────────┐
│   Worker SubAgent  │      │   Analyzer Agent   │
│  (fresh context)   │      │  - Problem Detect  │
│  - Execute tools   │      │  - Pattern Summary │
│  - Return summary  │      │  - Suggest Improve │
└────────────────────┘      └────────────────────┘

关键点: "子代理上下文隔离，只返回摘要给父代理"
"""

from __future__ import annotations

import json
import os
import re
import time
import hashlib
from pathlib import Path
from typing import Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

from loguru import logger

try:
    from .base import BaseAgentLoop, tool
    from .s05_skill_loading import SYSTEM as S05_SYSTEM, TOOLS as S05_TOOLS
    from .websocket.bridge import WebSocketBridge
except ImportError:
    from agents.base import BaseAgentLoop, tool
    from agents.s05_skill_loading import SYSTEM as S05_SYSTEM, TOOLS as S05_TOOLS
    from agents.websocket.bridge import WebSocketBridge


# ============================================================================
# Learning Memory System - 学习记忆系统
# ============================================================================

@dataclass
class ToolCallRecord:
    """单次工具调用记录"""
    tool_name: str
    tool_input: dict
    output: str
    success: bool
    error_type: str | None = None
    duration_ms: int = 0
    context_summary: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class PatternInsight:
    """模式洞察 - 从多次调用中总结的规律"""
    pattern_id: str
    tool_name: str
    pattern_description: str
    success_rate: float
    common_errors: list[str]
    recommendations: list[str]
    occurrence_count: int = 0


class LearningMemory:
    """
    学习记忆系统 - 持久化存储工具调用历史，识别成功/失败模式
    """

    def __init__(self, memory_dir: Path | None = None):
        self.memory_dir = memory_dir or Path(".agent_memory")
        self.memory_dir.mkdir(exist_ok=True)

        self.tool_history: list[ToolCallRecord] = []
        self.patterns: dict[str, PatternInsight] = {}
        self.session_stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "tool_breakdown": defaultdict(lambda: {"success": 0, "fail": 0}),
        }

        self._load_history()

    def record_call(self, record: ToolCallRecord):
        """记录一次工具调用"""
        self.tool_history.append(record)
        self.session_stats["total_calls"] += 1

        if record.success:
            self.session_stats["successful_calls"] += 1
            self.session_stats["tool_breakdown"][record.tool_name]["success"] += 1
        else:
            self.session_stats["failed_calls"] += 1
            self.session_stats["tool_breakdown"][record.tool_name]["fail"] += 1

        self._analyze_pattern(record)

        if len(self.tool_history) % 10 == 0:
            self._persist_history()

    def _analyze_pattern(self, record: ToolCallRecord):
        """分析调用模式，识别问题"""
        error_sig = record.error_type or "success"
        pattern_key = f"{record.tool_name}:{error_sig}"
        pattern_id = hashlib.md5(pattern_key.encode()).hexdigest()[:8]

        if pattern_id not in self.patterns:
            self.patterns[pattern_id] = PatternInsight(
                pattern_id=pattern_id,
                tool_name=record.tool_name,
                pattern_description=self._generate_pattern_desc(record),
                success_rate=1.0 if record.success else 0.0,
                common_errors=[] if record.success else [record.error_type or "unknown"],
                recommendations=self._generate_recommendations(record),
                occurrence_count=1
            )
        else:
            pattern = self.patterns[pattern_id]
            pattern.occurrence_count += 1
            total = pattern.occurrence_count
            successes = sum(1 for r in self.tool_history[-50:]
                          if r.tool_name == record.tool_name and r.success)
            pattern.success_rate = successes / min(total, 50)

            if not record.success and record.error_type:
                if record.error_type not in pattern.common_errors:
                    pattern.common_errors.append(record.error_type)

    def _generate_pattern_desc(self, record: ToolCallRecord) -> str:
        """生成模式描述"""
        if record.success:
            return f"{record.tool_name} successful execution pattern"
        else:
            error = record.error_type or "unknown error"
            return f"{record.tool_name} failure pattern: {error}"

    def _generate_recommendations(self, record: ToolCallRecord) -> list[str]:
        """基于记录生成改进建议"""
        recommendations = []

        if not record.success:
            if "sql" in record.tool_name.lower():
                if "syntax" in (record.error_type or "").lower():
                    recommendations.append("Use sql_validate before sql_execute")
                elif "timeout" in (record.error_type or "").lower():
                    recommendations.append("Reduce query complexity or add LIMIT clause")

            if "table" in (record.tool_name or "").lower() and "not found" in record.output.lower():
                recommendations.append("Use sql_describe_table to verify table existence first")

        return recommendations

    def get_insights_for_tool(self, tool_name: str) -> list[PatternInsight]:
        """获取指定工具的所有洞察"""
        return [p for p in self.patterns.values() if p.tool_name == tool_name]

    def get_session_summary(self) -> dict:
        """获取当前会话摘要"""
        recent_failures = [r for r in self.tool_history[-20:] if not r.success]

        return {
            "total_calls": self.session_stats["total_calls"],
            "success_rate": self.session_stats["successful_calls"] / max(self.session_stats["total_calls"], 1),
            "tool_breakdown": dict(self.session_stats["tool_breakdown"]),
            "recent_failures": [
                {"tool": r.tool_name, "error": r.error_type, "context": r.context_summary[:100]}
                for r in recent_failures[-5:]
            ],
        }

    def _load_history(self):
        """从磁盘加载历史"""
        history_file = self.memory_dir / "tool_history.jsonl"
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            data = json.loads(line)
                            self.tool_history.append(ToolCallRecord(**data))
            except Exception as e:
                logger.warning(f"Failed to load history: {e}")

    def _persist_history(self):
        """持久化历史到磁盘"""
        history_file = self.memory_dir / "tool_history.jsonl"
        try:
            with open(history_file, "w", encoding="utf-8") as f:
                for record in self.tool_history[-1000:]:
                    f.write(json.dumps(record.__dict__, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist history: {e}")


# ============================================================================
# Tool Call Monitor - 工具调用监控器
# ============================================================================

class ToolCallMonitor:
    """工具调用监控器 - 拦截和记录所有工具调用"""

    def __init__(self, learning_memory: LearningMemory):
        self.memory = learning_memory
        self._active_calls: dict[str, dict] = {}

    def wrap_tool(self, original_tool: Callable, tool_name: str) -> Callable:
        """包装工具函数，添加监控"""

        def monitored_tool(**kwargs):
            call_id = f"{tool_name}_{int(time.time() * 1000)}"
            start_time = time.time()

            self._active_calls[call_id] = {
                "tool_name": tool_name,
                "input": kwargs,
                "start_time": start_time
            }

            try:
                result = original_tool(**kwargs)
                success, error_type = self._analyze_result(result, tool_name)

                record = ToolCallRecord(
                    tool_name=tool_name,
                    tool_input=kwargs,
                    output=str(result)[:1000],
                    success=success,
                    error_type=error_type,
                    duration_ms=int((time.time() - start_time) * 1000),
                    context_summary=self._extract_context_summary(kwargs)
                )

                self.memory.record_call(record)
                del self._active_calls[call_id]

                return result

            except Exception as e:
                record = ToolCallRecord(
                    tool_name=tool_name,
                    tool_input=kwargs,
                    output=str(e)[:1000],
                    success=False,
                    error_type=type(e).__name__,
                    duration_ms=int((time.time() - start_time) * 1000),
                    context_summary=self._extract_context_summary(kwargs)
                )
                self.memory.record_call(record)
                del self._active_calls[call_id]
                raise

        if hasattr(original_tool, "__tool_spec__"):
            monitored_tool.__tool_spec__ = original_tool.__tool_spec__

        return monitored_tool

    def _analyze_result(self, result: Any, tool_name: str) -> tuple[bool, str | None]:
        """分析工具返回结果，判断是否成功"""
        result_str = str(result).lower()
        error_indicators = ["error:", "exception:", "failed", "timeout", "permission denied", "not found", "invalid"]

        for indicator in error_indicators:
            if indicator in result_str:
                return False, indicator.replace(":", "").strip()

        if "sql" in tool_name.lower():
            if result_str.count("{") > 0:
                try:
                    data = json.loads(result)
                    if isinstance(data, dict):
                        if data.get("ok") is False:
                            return False, "sql_validation_failed"
                        if "errors" in data and data["errors"]:
                            return False, "sql_execution_error"
                except:
                    pass

        return True, None

    def _extract_context_summary(self, kwargs: dict) -> str:
        """提取调用上下文摘要"""
        summary_parts = []
        for key, value in kwargs.items():
            if key in ["sql", "query", "prompt", "text", "content"]:
                val_str = str(value)[:50]
                summary_parts.append(f"{key}={val_str}...")
        return "; ".join(summary_parts) if summary_parts else "generic_call"


# ============================================================================
# Worker SubAgent - 子代理实现 (参考 s04 设计)
# ============================================================================

class WorkerSubAgent:
    """
    子代理 - 独立上下文执行，返回摘要给父代理

    设计原则 (来自 s04_subagent.py):
    1. 子代理有独立的 messages 上下文
    2. 子代理与父代理共享文件系统（通过相同的 tools）
    3. 子代理只返回摘要，完整上下文丢弃
    """

    WORKER_PROMPTS = {
        "sql_executor": """You are a SQL execution specialist.
Execute SQL queries efficiently and safely. Return concise summary of results.""",

        "schema_explorer": """You are a database schema exploration specialist.
Explore database structure and return key findings summary.""",

        "data_validator": """You are a data quality validation specialist.
Check data integrity and return validation summary.""",

        "analyzer": """You are a data analysis specialist.
Analyze data and return key insights summary.""",
    }

    def __init__(self, worker_type: str, provider: Any, model: str,
                 tools: list, callbacks: dict[str, Any] | None = None):
        if worker_type not in self.WORKER_PROMPTS:
            raise ValueError(f"Unknown worker type: {worker_type}")

        self.worker_type = worker_type
        self._callbacks = callbacks or {}

        # Debug: log should_stop callback
        has_stop = "should_stop" in self._callbacks and self._callbacks["should_stop"] is not None
        logger.info(f"[WorkerSubAgent:{worker_type}] should_stop callback present: {has_stop}")

        # 创建子代理的 BaseAgentLoop（不包含 task 工具，避免递归）
        self.loop = BaseAgentLoop(
            provider=provider,
            model=model,
            system=self.WORKER_PROMPTS[worker_type],
            tools=tools,
            max_tokens=8000,
            max_rounds=15,
            **self._callbacks
        )

    def run(self, objective: str, context: str = "") -> str:
        """
        运行子代理任务，返回摘要

        Args:
            objective: 任务目标
            context: 相关上下文信息

        Returns:
            任务执行摘要
        """
        # 构建 prompt (参考 s04 的 sub_messages = [{"role": "user", "content": prompt}])
        full_prompt = f"""Objective: {objective}

Context: {context or 'No additional context'}

Execute this task using available tools. Return your findings in a clear, structured format."""

        # 全新上下文 - 独立执行
        sub_messages = [{"role": "user", "content": full_prompt}]

        try:
            self.loop.run(sub_messages)

            # 提取最终结果（参考 s04 的 _extract_final_text）
            return self._extract_summary(sub_messages)

        except Exception as e:
            logger.error(f"Worker {self.worker_type} failed: {e}")
            return f"[Worker Error: {e}]"

    def _extract_summary(self, messages: list[dict]) -> str:
        """从子代理消息历史中提取摘要"""
        # 收集 assistant 的所有文本响应
        assistant_texts = []
        tool_calls_count = 0

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "assistant" and content:
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text = block.get("text", "").strip()
                                if text:
                                    assistant_texts.append(text)
                            elif block.get("type") == "tool_use":
                                tool_calls_count += 1
                        elif hasattr(block, "text"):
                            text = str(block.text).strip()
                            if text:
                                assistant_texts.append(text)
                elif isinstance(content, str) and content.strip():
                    assistant_texts.append(content.strip())

        # 构建摘要
        summary = "\n\n".join(assistant_texts) if assistant_texts else "(no response)"

        # 添加工具调用统计
        if tool_calls_count > 0:
            summary += f"\n\n[Executed {tool_calls_count} tool calls]"

        return summary


# ============================================================================
# Master Agent System Prompt
# ============================================================================

MASTER_SYSTEM = """You are the Master SQL Agent - an intelligent orchestrator for database operations.

## Your Role
You analyze user requests and delegate execution to specialized Worker SubAgents.
You do NOT execute tools directly - always use the `task` tool to delegate.

## Available Workers
1. **sql_executor** - Execute SQL queries and retrieve data
2. **schema_explorer** - Explore database structure and schema
3. **data_validator** - Validate data quality and integrity
4. **analyzer** - Analyze data and generate insights

## Delegation Process
1. Analyze the user's request
2. Choose appropriate worker type
3. Provide clear objective and context
4. Receive summary from worker
5. Integrate results and respond to user

## Key Rules
- ALWAYS use `task` tool to delegate to workers
- Provide sufficient context in delegation
- Review worker summaries carefully
- Ask follow-up questions if needed
- Present final results clearly to user

## Example Workflow
User: "Show me sales data"
→ You: task(worker_type="sql_executor", objective="Query sales data from the database", context="...")
← Worker: Returns summary with query results
→ You: Present formatted results to user
"""


# ============================================================================
# SQL Agent Loop V2 - 主循环
# ============================================================================

class SQLAgentLoopV2(BaseAgentLoop):
    """
    SQL Agent Loop V2 - 主-子代理架构 with 学习优化

    核心设计 (参考 s04_subagent.py):
    - 主代理专注决策，通过 task 工具委派给子代理
    - 子代理有独立上下文，执行完成后返回摘要
    - 子代理上下文不共享，每次委派都是全新的
    """

    def __init__(
        self,
        *,
        provider: Any,
        model: str,
        system: str = MASTER_SYSTEM,
        tools: list[Any] | None = None,
        max_tokens: int = 8000,
        max_rounds: int | None = 20,
        enable_learning: bool = True,
        memory_dir: Path | None = None,
        **base_kwargs
    ):
        # 初始化学习系统
        self.learning_memory = LearningMemory(memory_dir) if enable_learning else None

        # 准备工具列表
        base_tools = list(tools or S05_TOOLS)

        # 保存客户端配置供子代理使用
        self._client = provider
        self._model = model

        # 保存回调供子代理使用
        self._worker_callbacks = {
            k: v for k, v in base_kwargs.items()
            if (k.startswith("on_") or k == "should_stop") and v is not None
        }
        self._should_stop = base_kwargs.get("should_stop")

        # 创建 task 工具并添加
        task_tool = self._create_task_tool()
        base_tools.append(task_tool)

        # 如果需要，包装工具以启用监控
        if enable_learning:
            monitor = ToolCallMonitor(self.learning_memory)
            monitored_tools = []
            for tool_fn in base_tools:
                tool_name = getattr(tool_fn, "__tool_spec__", {}).get("name", "unknown")
                wrapped = monitor.wrap_tool(tool_fn, tool_name)
                monitored_tools.append(wrapped)
            base_tools = monitored_tools

        # 初始化基类
        super().__init__(
            provider=provider,
            model=model,
            system=system,
            tools=base_tools,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            **base_kwargs
        )

        logger.info(f"[SQLAgentLoopV2] Initialized with learning={enable_learning}")

    def _create_task_tool(self):
        """创建 task 工具用于子代理委派"""

        @tool(name="task", description="""Delegate a task to a specialized worker subagent.

Args:
    worker_type: Type of worker - 'sql_executor', 'schema_explorer', 'data_validator', or 'analyzer'
    objective: Clear description of what the worker should accomplish
    context: Relevant context, schema info, or constraints

Returns:
    Summary of the worker's execution results
""")
        def task(worker_type: str, objective: str, context: str = "") -> str:
            """
            委派任务给子代理

            参考 s04_subagent.py 的设计:
            - 创建独立上下文的子代理
            - 子代理执行完成后返回摘要
            - 子代理的完整上下文丢弃
            """
            logger.info(f"> task [{worker_type}]: {objective[:60]}...")
            logger.info(f"[task] Worker callbacks keys: {list(self._worker_callbacks.keys())}")
            logger.info(f"[task] has should_stop: {'should_stop' in self._worker_callbacks}")

            # 设置当前 agent_type 为 worker 类型
            prev_agent_type = getattr(WebSocketBridge, 'current_agent_type', None)
            WebSocketBridge.current_agent_type = f"worker:{worker_type}"

            try:
                # 创建子代理（每次全新实例，独立上下文）
                worker = WorkerSubAgent(
                    worker_type=worker_type,
                    client=self._client,
                    model=self._model,
                    tools=S05_TOOLS,  # 子代理使用基础工具（不含 task）
                    callbacks=self._worker_callbacks
                )

                # 运行子代理并获取摘要
                summary = worker.run(objective=objective, context=context)

                logger.info(f"< task [{worker_type}] result: {summary[:100]}...")
                return summary

            except Exception as e:
                logger.error(f"Task delegation failed: {e}")
                import traceback
                traceback.print_exc()
                return f"[Task Error: {e}]"

            finally:
                # 恢复 agent_type
                WebSocketBridge.current_agent_type = prev_agent_type

        return task


# ============================================================================
# Factory Function
# ============================================================================

def build_sql_agent_loop_v2(
    *,
    provider: Any,
    model: str,
    enable_learning: bool = True,
    memory_dir: Path | None = None,
    **kwargs
) -> SQLAgentLoopV2:
    """工厂函数：创建 SQLAgentLoopV2 实例"""
    return SQLAgentLoopV2(
        provider=provider,
        model=model,
        enable_learning=enable_learning,
        memory_dir=memory_dir,
        **kwargs
    )


__all__ = [
    "SQLAgentLoopV2",
    "LearningMemory",
    "ToolCallMonitor",
    "WorkerSubAgent",
    "build_sql_agent_loop_v2",
]
