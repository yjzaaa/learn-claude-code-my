"""
MemoryExtractor - 记忆提取服务

使用 LLM 分析对话并自动提取有价值的记忆信息。
支持结构化输出，返回 Memory 对象列表（未保存）。
"""

import json

from backend.domain.models.memory import Memory
from backend.domain.models.memory.types import MemoryType

# 记忆提取的 JSON Schema 定义
MEMORY_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "memories": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["user", "feedback", "project", "reference"],
                        "description": "记忆类型: user=用户信息, feedback=反馈指导, project=项目上下文, reference=外部引用",
                    },
                    "name": {
                        "type": "string",
                        "description": "记忆名称/标题，简洁描述这条记忆的核心内容",
                    },
                    "description": {
                        "type": "string",
                        "description": "简短描述（单行），补充说明记忆的上下文",
                    },
                    "content": {
                        "type": "string",
                        "description": "记忆的详细内容，包含所有重要信息",
                    },
                },
                "required": ["type", "name", "content"],
            },
        }
    },
    "required": ["memories"],
}

# 记忆提取系统提示词
MEMORY_EXTRACTION_SYSTEM_PROMPT = """You are a memory extraction assistant. Your task is to analyze conversations and extract valuable information worth remembering for future interactions.

Extract memories that fall into these categories:

1. **user** - User information, preferences, role, working style
   - User's job title, expertise level
   - Communication preferences (concise vs detailed)
   - Technical stack preferences
   - Working habits or constraints

2. **feedback** - Feedback guidance, behavior rules, improvement suggestions
   - What the user liked or disliked
   - Corrections to your previous responses
   - Style preferences (e.g., "prefer code over prose")
   - Rules for future interactions

3. **project** - Project context, goals, constraints, deadlines
   - Project objectives and requirements
   - Architecture decisions
   - Constraints (performance, compatibility, etc.)
   - Deadlines or milestones

4. **reference** - External references, documentation links, resource locations
   - Important URLs or documentation
   - File paths that are frequently referenced
   - External resources the user mentioned

Guidelines:
- Only extract information that would be useful in future conversations
- Be specific and concrete, avoid vague generalizations
- Focus on facts, preferences, and constraints, not transient details
- If no valuable memories can be extracted, return an empty memories array
- Each memory should be self-contained and understandable without context

Output must be valid JSON following the provided schema."""


class MemoryExtractor:
    """记忆提取服务

    使用 LLM 分析对话并自动提取有价值的记忆信息。
    返回的 Memory 对象未保存，需要调用方负责持久化。

    Attributes:
        _llm: LLM 提供者接口
    """

    def __init__(self, llm_provider):
        """初始化 MemoryExtractor

        Args:
            llm_provider: 实现 LLM 调用接口的对象，需要支持 generate/chat 方法
        """
        self._llm = llm_provider

    async def extract_from_conversation(
        self,
        messages: list[dict],
        user_id: str = "",
        project_path: str = "",
    ) -> list[Memory]:
        """从对话中提取记忆

        使用 LLM 分析对话内容，识别并提取有价值的记忆信息。
        返回的 Memory 对象列表未保存到仓库，需要调用方调用 save 方法。

        Args:
            messages: 对话消息列表，每条消息应为 dict，包含 role 和 content
            user_id: 用户ID，用于创建 Memory 对象
            project_path: 项目路径，用于创建 Memory 对象

        Returns:
            List[Memory]: 提取的记忆对象列表（未保存）
        """
        if not messages:
            return []

        # 构建提取提示
        conversation_text = self._format_messages(messages)

        prompt = f"""Please analyze the following conversation and extract valuable memories.

Conversation:
{conversation_text}

Extract memories according to the schema. Return valid JSON."""

        # 调用 LLM 进行提取
        try:
            response = await self._call_llm_with_schema(
                prompt=prompt,
                schema=MEMORY_EXTRACTION_SCHEMA,
            )

            if not response or "memories" not in response:
                return []

            # 解析并创建 Memory 对象
            memories = []
            for mem_data in response["memories"]:
                try:
                    memory = Memory(
                        user_id=user_id,
                        project_path=project_path,
                        type=MemoryType(mem_data["type"]),
                        name=mem_data["name"],
                        description=mem_data.get("description", ""),
                        content=mem_data["content"],
                    )
                    memories.append(memory)
                except (ValueError, KeyError):
                    # 跳过无效的记忆数据
                    continue

            return memories

        except Exception:
            # 提取失败时返回空列表
            return []

    def _format_messages(self, messages: list[dict]) -> str:
        """格式化消息列表为文本

        Args:
            messages: 消息字典列表

        Returns:
            str: 格式化后的对话文本
        """
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # 处理多模态内容（如果有）
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                content = " ".join(text_parts)

            role_label = {
                "user": "User",
                "assistant": "Assistant",
                "system": "System",
            }.get(role, role.capitalize())

            lines.append(f"{role_label}: {content}")

        return "\n\n".join(lines)

    async def _call_llm_with_schema(
        self,
        prompt: str,
        schema: dict,
    ) -> dict | None:
        """调用 LLM 并返回结构化 JSON 输出

        Args:
            prompt: 提示词
            schema: JSON Schema 定义

        Returns:
            Optional[Dict]: 解析后的 JSON 对象，失败时返回 None
        """
        # 构建包含 schema 的完整提示
        schema_prompt = f"""{prompt}

You must respond with valid JSON matching this schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

Response (JSON only):"""

        # 调用 LLM
        messages = [
            {"role": "system", "content": MEMORY_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": schema_prompt},
        ]

        try:
            # 尝试使用非流式调用获取完整响应
            if hasattr(self._llm, "generate"):
                response = await self._llm.generate(messages=messages)
                content = response if isinstance(response, str) else response.get("content", "")
            elif hasattr(self._llm, "chat"):
                response = await self._llm.chat(messages=messages)
                content = response if isinstance(response, str) else response.get("content", "")
            else:
                # 尝试使用流式方法并收集所有内容
                content_parts = []
                async for chunk in self._llm.chat_stream(messages=messages):
                    if hasattr(chunk, "content") and chunk.content:
                        content_parts.append(chunk.content)
                    elif isinstance(chunk, str):
                        content_parts.append(chunk)
                content = "".join(content_parts)

            if not content:
                return None

            # 清理响应内容（移除可能的 markdown 代码块标记）
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # 解析 JSON
            return json.loads(content)

        except json.JSONDecodeError:
            return None
        except Exception:
            return None
