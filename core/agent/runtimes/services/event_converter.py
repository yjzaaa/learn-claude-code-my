"""
Event Converter - 事件转换器

将 Deep Agent 流式事件转换为 AgentEvent。
"""
from typing import Any, Optional
from langchain_core.messages import BaseMessage, message_to_dict
from core.types import AgentEvent, ToolResult


def _extract_messages(state_update: Any) -> list[dict]:
    """从 updates 状态中提取消息列表，兼容 Overwrite / list / None"""
    if state_update is None:
        return []
    if hasattr(state_update, "get"):
        raw_msgs = state_update.get("messages")
    else:
        return []
    # 解包 LangGraph Overwrite
    if hasattr(raw_msgs, "value"):
        raw_msgs = raw_msgs.value
    if not isinstance(raw_msgs, list):
        return []
    return [message_to_dict(m) if isinstance(m, BaseMessage) else m for m in raw_msgs]


class StreamEventConverter:
    """流式事件转换器"""

    @staticmethod
    def convert(event: Any, dialog_id: str, accumulated: str) -> Optional[AgentEvent]:
        """
        将 Deep Agent 流式事件转换为 AgentEvent

        stream_mode="updates" 返回格式: {node_name: state_update}
        """
        if not isinstance(event, dict):
            return None

        for node_name, state_update in event.items():
            messages = _extract_messages(state_update)

            # model 节点产出完整 AIMessage - 这是我们需要的主要事件
            if node_name == "model":
                return AgentEvent(
                    type="model_complete",
                    data={"node": node_name, "messages": messages}
                )

            # 其他节点如果有 AI 消息也处理（某些配置下 model 节点可能命名不同）
            for msg in messages:
                if isinstance(msg, dict) and msg.get("type") == "ai":
                    return AgentEvent(
                        type="model_complete",
                        data={"node": node_name, "messages": messages}
                    )

            # 工具节点 - 提取工具调用信息
            if node_name in ("tools", "tool_executor"):
                # 从工具节点提取工具结果
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("type") == "tool":
                        return AgentEvent(
                            type="tool_end",
                            data={
                                "node": node_name,
                                "tool_call_id": msg.get("data", {}).get("tool_call_id", ""),
                                "content": msg.get("data", {}).get("content", ""),
                            }
                        )
                continue

            # 检查是否是AI消息但包含工具调用（tool_use决策）
            for msg in messages:
                if isinstance(msg, dict) and msg.get("type") == "ai":
                    content = msg.get("data", {}).get("content", "")
                    # 如果内容是列表且包含tool_use，生成tool_start事件
                    if isinstance(content, list):
                        tool_calls = [block for block in content if isinstance(block, dict) and block.get("type") == "tool_use"]
                        if tool_calls:
                            return AgentEvent(
                                type="tool_start",
                                data={
                                    "node": node_name,
                                    "tool_calls": tool_calls,
                                }
                            )

            # 其他内部节点事件不传递给前端
            continue

        return None


class EventConverter:
    """通用事件转换器"""

    @staticmethod
    def convert(event: Any) -> Optional[AgentEvent]:
        """转换事件为 AgentEvent"""
        if isinstance(event, AgentEvent):
            return event

        if isinstance(event, dict):
            event_type = event.get("type", "unknown")
            event_data = event.get("data", event)
            return AgentEvent(type=event_type, data=event_data)

        return AgentEvent(type="unknown", data=event)
