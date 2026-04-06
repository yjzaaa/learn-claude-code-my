"""
集成测试 - 验证所有 Pydantic 模型之间的交互和集成
"""

from datetime import datetime

import pytest

# 事件模型
from backend.domain.models.event_models import (
    TodoItemModel,
    TodoUpdatedEventModel,
    ToolCallStartedEventModel,
)

# 响应模型
from backend.domain.models.response_models import (
    APIAgentStatusResponse,
    APIHealthResponse,
    ResultModel,
)

# 工具模型
from backend.domain.models.tool_models import (
    JSONSchema,
    OpenAIFunctionSchema,
    OpenAIToolSchema,
    ToolSpec,
)

# WebSocket 模型
from backend.domain.models.websocket_models import (
    WSDeltaContent,
    WSDialogMetadata,
    WSDialogSnapshot,
    WSErrorDetail,
    WSErrorEvent,
    WSSnapshotEvent,
    WSStreamDeltaEvent,
    WSTodoItem,
    WSTodoUpdatedEvent,
    WSToolCall,
    WSToolCallUpdateEvent,
)


class TestToolToResponseIntegration:
    """测试工具模型与响应模型集成"""

    def test_tool_spec_to_api_response(self):
        """测试 ToolSpec 创建后通过 API 响应返回"""
        tool = ToolSpec(
            name="read_file",
            description="读取文件内容",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件路径"}
                },
                "required": ["path"],
            },
        )

        # 转换为 API 响应格式
        result = ResultModel.ok(
            message="工具创建成功",
            data={"tool": tool.model_dump()},
        )

        assert result.success is True
        assert result.data["tool"]["name"] == "read_file"
        assert result.data["tool"]["parameters"]["type"] == "object"

    def test_tool_validation_error_to_result(self):
        """测试工具验证错误转换为错误结果"""
        try:
            ToolSpec(name="", description="测试", parameters={})
        except Exception as e:
            result = ResultModel.error(message=str(e))
            assert result.success is False
            assert "name" in result.message.lower() or "empty" in result.message.lower()


class TestEventToWebSocketIntegration:
    """测试事件模型与 WebSocket 模型集成"""

    def test_todo_event_to_websocket_event(self):
        """测试 Todo 事件转换为 WebSocket 事件格式"""
        # 创建内部 Todo 项
        todo_item = TodoItemModel(
            id="todo-001",
            text="完成任务 A",
            status="in_progress",
        )

        # 创建内部事件
        internal_event = TodoUpdatedEventModel(
            dialog_id="dlg-001",
            todos=[todo_item],
            rounds_since_todo=3,
        )

        # 转换为 WebSocket 事件格式
        ws_event = WSTodoUpdatedEvent(
            dialog_id=internal_event.dialog_id,
            todos=[WSTodoItem(id=t.id, text=t.text, status=t.status) for t in internal_event.todos],
            rounds_since_todo=internal_event.rounds_since_todo,
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        assert ws_event.type == "todo:updated"
        assert ws_event.dialog_id == "dlg-001"
        assert len(ws_event.todos) == 1
        assert ws_event.todos[0].status == "in_progress"

    def test_tool_call_event_to_websocket(self):
        """测试工具调用事件转换为 WebSocket 事件"""
        # 内部工具调用开始事件
        start_event = ToolCallStartedEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
            arguments={"path": "/test.txt"},
        )

        # 转换为 WebSocket 工具调用格式
        ws_tool_call = WSToolCall(
            id=start_event.tool_call_id,
            name=start_event.tool_name,
            arguments=start_event.arguments,
            status="running",
        )

        ws_event = WSToolCallUpdateEvent(
            dialog_id=start_event.dialog_id,
            tool_call=ws_tool_call,
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        assert ws_event.type == "tool_call:update"
        assert ws_event.tool_call.name == "read_file"
        assert ws_event.tool_call.status == "running"


class TestFullWorkflowIntegration:
    """测试完整工作流集成"""

    def test_complete_dialog_workflow(self):
        """测试完整对话工作流中的模型交互"""
        # 1. 创建工具
        tool = ToolSpec(
            name="search",
            description="搜索工具",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
            },
        )

        # 2. 创建对话元数据
        metadata = WSDialogMetadata(
            model="claude-sonnet-4-6",
            agent_name="test-agent",
            tool_calls_count=1,
            total_tokens=150,
        )

        # 3. 创建对话快照
        snapshot = WSDialogSnapshot(
            id="dlg-001",
            title="测试对话",
            status="active",
            messages=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好！"},
            ],
            metadata=metadata,
            created_at="2024-01-01T00:00:00Z",
            updated_at="2024-01-01T00:01:00Z",
        )

        # 4. 创建快照事件
        snapshot_event = WSSnapshotEvent(
            dialog_id=snapshot.id,
            data=snapshot,
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        # 5. 创建增量事件
        delta_event = WSStreamDeltaEvent(
            dialog_id="dlg-001",
            message_id="msg-001",
            delta=WSDeltaContent(content="你好！", reasoning=""),
            timestamp=int(datetime.now().timestamp() * 1000),
        )

        # 6. 验证所有数据可以序列化
        snapshot_json = snapshot_event.model_dump_json()
        delta_json = delta_event.model_dump_json()

        assert "dialog:snapshot" in snapshot_json
        assert "stream:delta" in delta_json
        assert "test-agent" in snapshot_json

    def test_error_handling_workflow(self):
        """测试错误处理工作流"""
        # 模拟工具调用失败
        try:
            raise ValueError("工具执行失败: 文件不存在")
        except Exception as e:
            # 创建错误详情
            error_detail = WSErrorDetail(
                code="TOOL_EXECUTION_ERROR",
                message=str(e),
            )

            # 创建 WebSocket 错误事件
            error_event = WSErrorEvent(
                dialog_id="dlg-001",
                error=error_detail,
                timestamp=int(datetime.now().timestamp() * 1000),
            )

            assert error_event.error.code == "TOOL_EXECUTION_ERROR"
            assert "工具执行失败" in error_event.error.message


class TestSerializationRoundTrip:
    """测试序列化/反序列化往返"""

    def test_tool_spec_round_trip(self):
        """测试 ToolSpec 序列化往返"""
        original = ToolSpec(
            name="write_file",
            description="写入文件",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        )

        # 序列化
        data = original.model_dump()
        json_str = original.model_dump_json()

        # 反序列化
        restored_from_dict = ToolSpec.model_validate(data)
        restored_from_json = ToolSpec.model_validate_json(json_str)

        assert restored_from_dict.name == original.name
        assert restored_from_dict.description == original.description
        assert restored_from_json.name == original.name

    def test_complex_nested_model_round_trip(self):
        """测试复杂嵌套模型往返"""
        original = WSSnapshotEvent(
            dialog_id="dlg-001",
            data=WSDialogSnapshot(
                id="dlg-001",
                title="测试",
                status="active",
                messages=[{"role": "user", "content": "测试"}],
                metadata=WSDialogMetadata(
                    model="gpt-4",
                    agent_name="agent-1",
                    tool_calls_count=5,
                    total_tokens=1000,
                ),
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:01:00Z",
            ),
            timestamp=1234567890,
        )

        # 序列化和反序列化
        data = original.model_dump()
        restored = WSSnapshotEvent.model_validate(data)

        assert restored.dialog_id == original.dialog_id
        assert restored.data.title == original.data.title
        assert restored.data.metadata.model == "gpt-4"


class TestAPIResponsePatterns:
    """测试 API 响应模式"""

    def test_health_response(self):
        """测试健康检查响应"""
        response = APIHealthResponse(
            status="healthy",
            dialogs=10,
        )
        data = response.model_dump()

        assert data["status"] == "healthy"
        assert data["dialogs"] == 10

    def test_agent_status_response(self):
        """测试 Agent 状态响应"""
        from backend.domain.models.response_models import APIAgentStatusData, APIAgentStatusItem

        response = APIAgentStatusResponse(
            success=True,
            data=APIAgentStatusData(
                active_dialogs=[
                    APIAgentStatusItem(dialog_id="dlg-1", status="active"),
                    APIAgentStatusItem(dialog_id="dlg-2", status="paused"),
                ],
                total_dialogs=2,
            ),
        )

        assert response.success is True
        assert len(response.data.active_dialogs) == 2
        assert response.data.total_dialogs == 2


class TestValidationErrors:
    """测试验证错误处理"""

    def test_tool_spec_validation(self):
        """测试 ToolSpec 验证错误"""
        with pytest.raises(Exception) as exc_info:
            ToolSpec(name="", description="测试", parameters={})
        assert "name" in str(exc_info.value).lower() or "empty" in str(exc_info.value).lower()

    def test_json_schema_type_validation(self):
        """测试 JSONSchema 类型验证"""
        with pytest.raises(Exception) as exc_info:
            JSONSchema(type="invalid_type", properties={})
        assert "type" in str(exc_info.value).lower() or "object" in str(exc_info.value).lower()

    def test_openai_tool_schema_validation(self):
        """测试 OpenAIToolSchema 验证"""
        with pytest.raises(Exception) as exc_info:
            OpenAIToolSchema(type="invalid", function=OpenAIFunctionSchema(
                name="test",
                description="test",
                parameters={},
            ))
        assert "function" in str(exc_info.value).lower() or "type" in str(exc_info.value).lower()


class TestBackwardCompatibility:
    """测试向后兼容性"""

    def test_legacy_dict_to_pydantic(self):
        """测试旧字典格式转换为 Pydantic 模型"""
        # 模拟旧格式的数据
        legacy_data = {
            "name": "legacy_tool",
            "description": "旧版工具",
            "parameters": {
                "type": "object",
                "properties": {
                    "arg1": {"type": "string"},
                },
            },
        }

        # 应该能成功转换为 Pydantic 模型
        tool = ToolSpec.model_validate(legacy_data)
        assert tool.name == "legacy_tool"
        assert tool.parameters["type"] == "object"

    def test_pydantic_to_dict_for_legacy_api(self):
        """测试 Pydantic 模型转换为字典供旧 API 使用"""
        tool = ToolSpec(
            name="modern_tool",
            description="新版工具",
            parameters={"type": "object", "properties": {}},
        )

        # 转换为字典
        data = tool.model_dump()

        # 验证字典格式正确
        assert isinstance(data, dict)
        assert data["name"] == "modern_tool"
        assert "parameters" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
