"""
Execution Analyzer - 执行分析器

分析任务执行结果，识别错误模式，生成改进建议。
支持 LLM-based 深度分析和异步非阻塞执行。
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from backend.domain.models.agent.skill_engine_types import ExecutionAnalysis
from backend.infrastructure.config import config
from backend.infrastructure.logging import get_logger

logger = get_logger(__name__)

# Error pattern definitions
ERROR_PATTERNS = {
    "missing_tool": {
        "patterns": [
            r"tool not found",
            r"unknown tool",
            r"tool .* does not exist",
            r"no tool named",
            r"invalid tool",
        ],
        "suggestion": "Add explicit tool availability check in skill instructions. List required tools at the beginning of the skill.",
    },
    "parameter_error": {
        "patterns": [
            r"invalid parameter",
            r"parameter .* is required",
            r"missing required argument",
            r"type error",
            r"validation error",
            r"invalid argument",
        ],
        "suggestion": "Clarify parameter format with examples. Add parameter validation examples in the skill.",
    },
    "timeout": {
        "patterns": [
            r"timeout",
            r"timed out",
            r"deadline exceeded",
            r"execution time exceeded",
        ],
        "suggestion": "Break down long-running operations into smaller steps. Add timeout handling instructions.",
    },
    "permission_denied": {
        "patterns": [
            r"permission denied",
            r"access denied",
            r"unauthorized",
            r"forbidden",
            r"not allowed",
        ],
        "suggestion": "Add permission check instructions. Document required permissions for the skill.",
    },
    "file_not_found": {
        "patterns": [
            r"file not found",
            r"no such file",
            r"path does not exist",
            r"directory not found",
        ],
        "suggestion": "Add file existence checks before operations. Use relative paths from skill directory.",
    },
    "syntax_error": {
        "patterns": [
            r"syntax error",
            r"parse error",
            r"invalid syntax",
            r"unexpected token",
        ],
        "suggestion": "Review code examples in skill for syntax correctness. Add language-specific syntax notes.",
    },
    "dependency_error": {
        "patterns": [
            r"module not found",
            r"package not found",
            r"import error",
            r"no module named",
            r"dependency not found",
        ],
        "suggestion": "List required dependencies in skill documentation. Add installation instructions.",
    },
}


@dataclass
class ToolExecutionRecord:
    """工具执行记录"""

    tool_name: str
    parameters: dict[str, Any]
    success: bool
    error_message: str = ""
    execution_time_ms: int = 0


@dataclass
class ExecutionContext:
    """执行上下文"""

    task_id: str
    skill_ids: list[str] = field(default_factory=list)
    conversation_log: list[dict[str, Any]] = field(default_factory=list)
    tool_executions: list[ToolExecutionRecord] = field(default_factory=list)
    final_output: str = ""
    success: bool = False
    error_message: str = ""
    execution_time_ms: int = 0


class ExecutionAnalyzer:
    """执行分析器

    分析任务执行结果，识别错误模式，生成改进建议。

    Attributes:
        _llm_client: LLM 客户端（可选）
        _analysis_history: 分析历史记录
    """

    def __init__(self, llm_client: Any | None = None):
        """初始化 ExecutionAnalyzer

        Args:
            llm_client: LLM 客户端实例（可选）
        """
        self._llm_client = llm_client
        self._analysis_history: list[dict[str, Any]] = []

    def analyze_sync(
        self,
        context: ExecutionContext,
        use_llm: bool = True,
    ) -> ExecutionAnalysis:
        """同步分析执行结果

        Args:
            context: 执行上下文
            use_llm: 是否使用 LLM 进行深度分析

        Returns:
            执行分析结果
        """
        return asyncio.run(self.analyze(context, use_llm))

    async def analyze(
        self,
        context: ExecutionContext,
        use_llm: bool = True,
    ) -> ExecutionAnalysis:
        """分析执行结果

        Args:
            context: 执行上下文
            use_llm: 是否使用 LLM 进行深度分析

        Returns:
            执行分析结果
        """
        try:
            # 1. 识别错误模式
            error_pattern = self._detect_error_pattern(context)

            # 2. 生成改进建议
            suggestion = self._generate_suggestion(context, error_pattern)

            # 3. 判断是否适合进化
            candidate_for_evolution = self._check_evolution_candidacy(
                context, error_pattern
            )

            # 4. 如果使用 LLM，进行深度分析
            if use_llm and self._llm_client:
                llm_analysis = await self._analyze_with_llm(context)
                if llm_analysis:
                    # 合并 LLM 分析结果
                    if llm_analysis.get("error_pattern"):
                        error_pattern = llm_analysis["error_pattern"]
                    if llm_analysis.get("suggested_improvement"):
                        suggestion = llm_analysis["suggested_improvement"]
                    if llm_analysis.get("candidate_for_evolution") is not None:
                        candidate_for_evolution = llm_analysis["candidate_for_evolution"]

            analysis = ExecutionAnalysis(
                success=context.success,
                error_pattern=error_pattern,
                suggested_improvement=suggestion,
                candidate_for_evolution=candidate_for_evolution,
                execution_time_ms=context.execution_time_ms,
                tool_calls_count=len(context.tool_executions),
            )

            # 记录分析历史
            self._record_analysis(context, analysis)

            return analysis

        except Exception as e:
            logger.error(f"[ExecutionAnalyzer] Analysis failed: {e}")
            # 返回基本分析结果
            return ExecutionAnalysis(
                success=context.success,
                error_pattern="analysis_failed",
                suggested_improvement=None,
                candidate_for_evolution=False,
                execution_time_ms=context.execution_time_ms,
                tool_calls_count=len(context.tool_executions),
            )

    def analyze_async(
        self,
        context: ExecutionContext,
        callback: callable | None = None,
    ) -> None:
        """异步分析（非阻塞）

        在后台执行分析，不阻塞主流程。

        Args:
            context: 执行上下文
            callback: 分析完成后的回调函数
        """

        async def _analyze_and_callback():
            try:
                analysis = await self.analyze(context, use_llm=True)
                if callback:
                    callback(analysis)
            except Exception as e:
                logger.error(f"[ExecutionAnalyzer] Async analysis failed: {e}")

        # 创建后台任务
        try:
            asyncio.create_task(_analyze_and_callback(), name="execution_analysis")
            logger.debug("[ExecutionAnalyzer] Started async analysis")
        except Exception as e:
            logger.error(f"[ExecutionAnalyzer] Failed to start async analysis: {e}")

    def _detect_error_pattern(self, context: ExecutionContext) -> str | None:
        """检测错误模式

        Args:
            context: 执行上下文

        Returns:
            错误模式标识或 None
        """
        if context.success:
            return None

        # 收集所有错误文本
        error_texts = []
        if context.error_message:
            error_texts.append(context.error_message.lower())

        for tool_exec in context.tool_executions:
            if not tool_exec.success and tool_exec.error_message:
                error_texts.append(tool_exec.error_message.lower())

        error_text = " ".join(error_texts)

        # 匹配错误模式
        for pattern_name, pattern_data in ERROR_PATTERNS.items():
            for pattern in pattern_data["patterns"]:
                if re.search(pattern, error_text, re.IGNORECASE):
                    logger.debug(f"[ExecutionAnalyzer] Detected error pattern: {pattern_name}")
                    return pattern_name

        return "unknown_error"

    def _generate_suggestion(
        self,
        context: ExecutionContext,
        error_pattern: str | None,
    ) -> str | None:
        """生成改进建议

        Args:
            context: 执行上下文
            error_pattern: 错误模式

        Returns:
            改进建议或 None
        """
        if context.success:
            return None

        if error_pattern and error_pattern in ERROR_PATTERNS:
            return ERROR_PATTERNS[error_pattern]["suggestion"]

        # 通用建议
        if context.tool_executions:
            failed_tools = [
                t.tool_name for t in context.tool_executions if not t.success
            ]
            if failed_tools:
                return f"Review failed tool executions: {', '.join(failed_tools)}. Check tool parameters and preconditions."

        return "Review execution logs for detailed error information."

    def _check_evolution_candidacy(
        self,
        context: ExecutionContext,
        error_pattern: str | None,
    ) -> bool:
        """检查是否适合进化

        Args:
            context: 执行上下文
            error_pattern: 错误模式

        Returns:
            是否适合进化
        """
        # 成功任务：检查是否有新颖的成功模式
        if context.success:
            # 如果使用了多个工具且成功，可能是好的模式
            if len(context.tool_executions) >= 3:
                return True
            return False

        # 失败任务：检查是否是可修复的错误
        if error_pattern in [
            "missing_tool",
            "parameter_error",
            "file_not_found",
            "permission_denied",
        ]:
            return True

        return False

    async def _analyze_with_llm(self, context: ExecutionContext) -> dict[str, Any] | None:
        """使用 LLM 进行深度分析

        Args:
            context: 执行上下文

        Returns:
            LLM 分析结果或 None
        """
        if not self._llm_client:
            return None

        try:
            # 构建分析提示
            prompt = self._build_analysis_prompt(context)

            # 调用 LLM
            response = await self._llm_client.complete(
                prompt=prompt,
                max_tokens=500,
                temperature=0.3,
            )

            # 解析响应
            return self._parse_llm_response(response)

        except Exception as e:
            logger.error(f"[ExecutionAnalyzer] LLM analysis failed: {e}")
            return None

    def _build_analysis_prompt(self, context: ExecutionContext) -> str:
        """构建 LLM 分析提示

        Args:
            context: 执行上下文

        Returns:
            分析提示
        """
        # 构建工具执行摘要
        tool_summary = []
        for i, tool_exec in enumerate(context.tool_executions[-10:], 1):  # 最近 10 个
            status = "✓" if tool_exec.success else "✗"
            tool_summary.append(
                f"{i}. {status} {tool_exec.tool_name}"
                f"{' - ' + tool_exec.error_message if not tool_exec.success else ''}"
            )

        tool_summary_str = "\n".join(tool_summary) if tool_summary else "No tool executions"

        # 构建对话摘要
        conversation_summary = ""
        if context.conversation_log:
            last_messages = context.conversation_log[-5:]  # 最近 5 条
            conversation_summary = "\n".join(
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}..."
                for msg in last_messages
            )

        prompt = f"""Analyze the following task execution and provide insights.

## Task Information
- Task ID: {context.task_id}
- Skills Used: {', '.join(context.skill_ids) if context.skill_ids else 'None'}
- Success: {context.success}
- Execution Time: {context.execution_time_ms}ms
- Tool Calls: {len(context.tool_executions)}

## Tool Execution Summary
{tool_summary_str}

## Recent Conversation
{conversation_summary}

## Error Information
{context.error_message if context.error_message else 'No error message'}

Please analyze this execution and provide:
1. Error pattern (if failed): missing_tool, parameter_error, timeout, permission_denied, file_not_found, syntax_error, dependency_error, or unknown_error
2. Suggested improvement: A specific, actionable suggestion to fix or improve
3. Candidate for evolution: true if this skill could be improved based on this execution, false otherwise

Respond in JSON format:
{{
    "error_pattern": "pattern_name or null",
    "suggested_improvement": "specific suggestion or null",
    "candidate_for_evolution": true/false,
    "brief_analysis": "one sentence summary"
}}"""

        return prompt

    def _parse_llm_response(self, response: str) -> dict[str, Any] | None:
        """解析 LLM 响应

        Args:
            response: LLM 响应文本

        Returns:
            解析后的字典或 None
        """
        try:
            # 尝试直接解析 JSON
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        # 尝试从文本中提取 JSON
        try:
            # 查找 JSON 代码块
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))

            # 查找花括号包裹的内容
            json_match = re.search(r'(\{.*\})', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

        logger.warning(f"[ExecutionAnalyzer] Failed to parse LLM response: {response[:200]}...")
        return None

    def _record_analysis(
        self,
        context: ExecutionContext,
        analysis: ExecutionAnalysis,
    ) -> None:
        """记录分析结果

        Args:
            context: 执行上下文
            analysis: 分析结果
        """
        record = {
            "task_id": context.task_id,
            "timestamp": datetime.utcnow().isoformat(),
            "success": analysis.success,
            "error_pattern": analysis.error_pattern,
            "suggested_improvement": analysis.suggested_improvement,
            "candidate_for_evolution": analysis.candidate_for_evolution,
            "skill_ids": context.skill_ids,
        }

        self._analysis_history.append(record)

        # 限制历史记录大小
        if len(self._analysis_history) > 1000:
            self._analysis_history = self._analysis_history[-500:]

    def save_analysis_to_metadata(
        self,
        task_id: str,
        analysis: ExecutionAnalysis,
        recording_dir: Path | str,
    ) -> bool:
        """保存分析结果到 metadata.json

        Args:
            task_id: 任务 ID
            analysis: 分析结果
            recording_dir: 录制目录路径

        Returns:
            是否成功保存
        """
        try:
            metadata_path = Path(recording_dir) / "metadata.json"

            # 读取现有 metadata
            metadata: dict[str, Any] = {}
            if metadata_path.exists():
                with open(metadata_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

            # 添加分析结果
            metadata["execution_analysis"] = {
                "task_id": task_id,
                "success": analysis.success,
                "error_pattern": analysis.error_pattern,
                "suggested_improvement": analysis.suggested_improvement,
                "candidate_for_evolution": analysis.candidate_for_evolution,
                "execution_time_ms": analysis.execution_time_ms,
                "tool_calls_count": analysis.tool_calls_count,
                "analyzed_at": datetime.utcnow().isoformat(),
            }

            # 写回文件
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.debug(f"[ExecutionAnalyzer] Saved analysis to {metadata_path}")
            return True

        except Exception as e:
            logger.error(f"[ExecutionAnalyzer] Failed to save analysis: {e}")
            return False

    def get_analysis_history(
        self,
        skill_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """获取分析历史

        Args:
            skill_id: 技能 ID 过滤（可选）
            limit: 返回记录数限制

        Returns:
            分析历史记录列表
        """
        history = self._analysis_history

        if skill_id:
            history = [
                h for h in history
                if skill_id in h.get("skill_ids", [])
            ]

        return history[-limit:]

    def get_error_pattern_stats(self) -> dict[str, int]:
        """获取错误模式统计

        Returns:
            错误模式 -> 出现次数
        """
        stats: dict[str, int] = {}

        for record in self._analysis_history:
            if not record.get("success"):
                pattern = record.get("error_pattern", "unknown")
                stats[pattern] = stats.get(pattern, 0) + 1

        return stats


__all__ = [
    "ExecutionAnalyzer",
    "ExecutionContext",
    "ToolExecutionRecord",
]
