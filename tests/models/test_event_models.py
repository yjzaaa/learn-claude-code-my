"""
事件模型测试 - 验证 Pydantic 事件模型的创建、验证和序列化
"""

from datetime import datetime

import pytest

from backend.domain.models.event_models import (
    EventModel,
    SkillEditEventModel,
    TodoEventModel,
    TodoItemModel,
    TodoReminderEventModel,
    TodoStatus,
    TodoUpdatedEventModel,
    ToolCallCompletedEventModel,
    ToolCallEventModel,
    ToolCallStartedEventModel,
)


class TestEventModel:
    """测试事件模型基类"""

    def test_event_model_creation(self):
        """测试事件模型基本创建"""
        event = EventModel(type="test")
        assert event.type == "test"
        assert isinstance(event.timestamp, float)
        assert event.timestamp > 0

    def test_event_model_default_timestamp(self):
        """测试时间戳默认值自动生成"""
        before = datetime.now().timestamp()
        event = EventModel(type="test")
        after = datetime.now().timestamp()

        assert before <= event.timestamp <= after

    def test_event_model_custom_timestamp(self):
        """测试自定义时间戳"""
        custom_ts = 1234567890.0
        event = EventModel(type="test", timestamp=custom_ts)
        assert event.timestamp == custom_ts


class TestSkillEditEventModel:
    """测试 SkillEdit 事件模型"""

    def test_skill_edit_event_creation(self):
        """测试 SkillEdit 事件创建"""
        event = SkillEditEventModel(
            dialog_id="dlg-001",
            approval_id="approval-001",
        )
        assert event.type == "skill_edit"
        assert event.dialog_id == "dlg-001"
        assert event.approval_id == "approval-001"

    def test_skill_edit_event_custom_type(self):
        """测试 SkillEdit 事件可覆盖类型"""
        event = SkillEditEventModel(
            type="custom_skill_edit",
            dialog_id="dlg-001",
            approval_id="approval-001",
        )
        assert event.type == "custom_skill_edit"


class TestTodoEventModel:
    """测试 Todo 事件模型"""

    def test_todo_event_creation(self):
        """测试 Todo 事件创建"""
        event = TodoEventModel(
            dialog_id="dlg-001",
            message="添加新任务",
        )
        assert event.type == "todo"
        assert event.dialog_id == "dlg-001"
        assert event.message == "添加新任务"


class TestTodoItemModel:
    """测试 TodoItem 模型"""

    def test_todo_item_creation(self):
        """测试 TodoItem 基本创建"""
        item = TodoItemModel(
            id="todo-001",
            text="完成任务 A",
        )
        assert item.id == "todo-001"
        assert item.text == "完成任务 A"
        assert item.status == "pending"  # 默认值

    def test_todo_item_with_status(self):
        """测试指定状态的 TodoItem"""
        item = TodoItemModel(
            id="todo-002",
            text="进行中任务",
            status="in_progress",
        )
        assert item.status == "in_progress"

    def test_todo_item_status_validation_valid(self):
        """测试状态验证 - 有效值"""
        for status in ["pending", "in_progress", "completed"]:
            item = TodoItemModel(id="t1", text="任务", status=status)
            assert item.status == status

    def test_todo_item_status_validation_invalid(self):
        """测试状态验证 - 无效值应返回默认值"""
        item = TodoItemModel(
            id="todo-003",
            text="任务",
            status="invalid_status",
        )
        assert item.status == "pending"  # 无效值应返回默认值


class TestTodoUpdatedEventModel:
    """测试 Todo 更新事件模型"""

    def test_todo_updated_event_creation(self):
        """测试 Todo 更新事件创建"""
        todos = [
            TodoItemModel(id="t1", text="任务 1"),
            TodoItemModel(id="t2", text="任务 2", status="completed"),
        ]
        event = TodoUpdatedEventModel(
            dialog_id="dlg-001",
            todos=todos,
        )
        assert event.type == "todo:updated"
        assert event.dialog_id == "dlg-001"
        assert len(event.todos) == 2
        assert event.rounds_since_todo == 0  # 默认值

    def test_todo_updated_event_with_rounds(self):
        """测试带 rounds_since_todo 的更新事件"""
        event = TodoUpdatedEventModel(
            dialog_id="dlg-001",
            todos=[],
            rounds_since_todo=5,
        )
        assert event.rounds_since_todo == 5


class TestTodoReminderEventModel:
    """测试 Todo 提醒事件模型"""

    def test_todo_reminder_event_creation(self):
        """测试 Todo 提醒事件创建"""
        event = TodoReminderEventModel(
            dialog_id="dlg-001",
            message="请继续处理未完成任务",
        )
        assert event.type == "todo:reminder"
        assert event.dialog_id == "dlg-001"
        assert event.message == "请继续处理未完成任务"
        assert event.rounds_since_todo == 0


class TestToolCallEventModel:
    """测试工具调用事件模型"""

    def test_tool_call_event_creation(self):
        """测试工具调用事件基本创建"""
        event = ToolCallEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
        )
        assert event.type == "tool_call"
        assert event.dialog_id == "dlg-001"
        assert event.tool_name == "read_file"
        assert event.tool_call_id == "call-001"
        assert event.arguments == {}  # 默认空字典

    def test_tool_call_event_with_arguments(self):
        """测试带参数的工具调用事件"""
        event = ToolCallEventModel(
            dialog_id="dlg-001",
            tool_name="write_file",
            tool_call_id="call-002",
            arguments={"file_path": "/test.txt", "content": "hello"},
        )
        assert event.arguments["file_path"] == "/test.txt"
        assert event.arguments["content"] == "hello"


class TestToolCallStartedEventModel:
    """测试工具调用开始事件模型"""

    def test_tool_call_started_event_creation(self):
        """测试工具调用开始事件创建"""
        event = ToolCallStartedEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
        )
        assert event.type == "tool_call:started"
        assert event.tool_name == "read_file"


class TestToolCallCompletedEventModel:
    """测试工具调用完成事件模型"""

    def test_tool_call_completed_event_creation(self):
        """测试工具调用完成事件基本创建"""
        event = ToolCallCompletedEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
        )
        assert event.type == "tool_call:completed"
        assert event.result is None
        assert event.error is None

    def test_tool_call_completed_with_result(self):
        """测试带结果的成功完成事件"""
        event = ToolCallCompletedEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
            result="文件内容",
        )
        assert event.result == "文件内容"
        assert event.error is None

    def test_tool_call_completed_with_error(self):
        """测试带错误的失败完成事件"""
        event = ToolCallCompletedEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
            error="文件不存在",
        )
        assert event.result is None
        assert event.error == "文件不存在"


class TestSerialization:
    """测试序列化和反序列化"""

    def test_event_serialization_to_dict(self):
        """测试事件序列化为字典"""
        event = SkillEditEventModel(
            dialog_id="dlg-001",
            approval_id="approval-001",
        )
        data = event.model_dump()

        assert data["type"] == "skill_edit"
        assert data["dialog_id"] == "dlg-001"
        assert data["approval_id"] == "approval-001"
        assert "timestamp" in data

    def test_event_deserialization_from_dict(self):
        """测试从字典反序列化事件"""
        data = {
            "type": "todo",
            "dialog_id": "dlg-001",
            "message": "测试消息",
            "timestamp": 1234567890.0,
        }
        event = TodoEventModel.model_validate(data)

        assert event.type == "todo"
        assert event.dialog_id == "dlg-001"
        assert event.message == "测试消息"
        assert event.timestamp == 1234567890.0

    def test_nested_model_serialization(self):
        """测试嵌套模型序列化"""
        event = TodoUpdatedEventModel(
            dialog_id="dlg-001",
            todos=[
                TodoItemModel(id="t1", text="任务 1", status="completed"),
            ],
            rounds_since_todo=3,
        )
        data = event.model_dump()

        assert data["type"] == "todo:updated"
        assert len(data["todos"]) == 1
        assert data["todos"][0]["id"] == "t1"
        assert data["todos"][0]["status"] == "completed"

    def test_json_serialization(self):
        """测试 JSON 序列化"""
        event = ToolCallStartedEventModel(
            dialog_id="dlg-001",
            tool_name="read_file",
            tool_call_id="call-001",
            arguments={"path": "/test.txt"},
        )
        json_str = event.model_dump_json()

        assert "tool_call:started" in json_str
        assert "read_file" in json_str
        assert "call-001" in json_str

    def test_backward_compatibility_with_extra_fields(self):
        """测试对额外字段的兼容性 - Pydantic 默认允许额外字段"""
        data = {
            "type": "todo",
            "dialog_id": "dlg-001",
            "message": "测试",
            "extra_field": "extra_value",
        }
        # Pydantic v2 默认允许额外字段
        event = TodoEventModel.model_validate(data)
        assert event.dialog_id == "dlg-001"
        assert event.message == "测试"


class TestTodoStatusEnum:
    """测试 TodoStatus 枚举"""

    def test_todo_status_values(self):
        """测试 TodoStatus 枚举值"""
        assert TodoStatus.PENDING == "pending"
        assert TodoStatus.IN_PROGRESS == "in_progress"
        assert TodoStatus.COMPLETED == "completed"

    def test_todo_status_from_string(self):
        """测试从字符串创建 TodoStatus"""
        assert TodoStatus("pending") == TodoStatus.PENDING
        assert TodoStatus("in_progress") == TodoStatus.IN_PROGRESS
        assert TodoStatus("completed") == TodoStatus.COMPLETED


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
