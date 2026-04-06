"""
Test Memory Domain Models - 记忆领域模型测试

测试 Memory, MemoryMetadata, MemoryType 的核心功能。
"""

from datetime import datetime, timedelta

from backend.domain.models.memory import Memory, MemoryMetadata, MemoryType


class TestMemoryType:
    """测试 MemoryType 枚举"""

    def test_memory_type_values(self):
        """测试记忆类型值"""
        assert MemoryType.USER == "user"
        assert MemoryType.FEEDBACK == "feedback"
        assert MemoryType.PROJECT == "project"
        assert MemoryType.REFERENCE == "reference"

    def test_memory_type_enum_members(self):
        """测试枚举成员"""
        assert len(list(MemoryType)) == 4


class TestMemoryMetadata:
    """测试 MemoryMetadata 模型"""

    def test_create_metadata(self):
        """测试创建元数据"""
        now = datetime.now()
        metadata = MemoryMetadata(
            id="test_123",
            user_id="user_456",
            project_path="/test/project",
            type=MemoryType.USER,
            name="Test Memory",
            description="A test memory",
            created_at=now,
            updated_at=now,
            age_days=0,
        )

        assert metadata.id == "test_123"
        assert metadata.user_id == "user_456"
        assert metadata.type == MemoryType.USER
        assert metadata.is_fresh is True

    def test_freshness_text_today(self):
        """测试今天的新鲜度文本"""
        metadata = MemoryMetadata(
            id="test_1",
            user_id="user_1",
            type=MemoryType.USER,
            name="Test",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            age_days=0,
        )
        assert metadata.freshness_text == "today"
        assert metadata.is_fresh is True
        assert metadata.freshness_warning == ""

    def test_freshness_text_yesterday(self):
        """测试昨天的新鲜度文本"""
        metadata = MemoryMetadata(
            id="test_1",
            user_id="user_1",
            type=MemoryType.USER,
            name="Test",
            created_at=datetime.now() - timedelta(days=1),
            updated_at=datetime.now() - timedelta(days=1),
            age_days=1,
        )
        assert metadata.freshness_text == "yesterday"
        assert metadata.is_fresh is True

    def test_freshness_text_days_ago(self):
        """测试多天前的新鲜度文本"""
        metadata = MemoryMetadata(
            id="test_1",
            user_id="user_1",
            type=MemoryType.USER,
            name="Test",
            created_at=datetime.now() - timedelta(days=5),
            updated_at=datetime.now() - timedelta(days=5),
            age_days=5,
        )
        assert metadata.freshness_text == "5 days ago"
        assert metadata.is_fresh is False
        assert "5 days ago" in metadata.freshness_warning


class TestMemory:
    """测试 Memory 实体"""

    def test_create_memory(self):
        """测试创建记忆"""
        memory = Memory(
            user_id="user_123",
            project_path="/my/project",
            type=MemoryType.USER,
            name="User Preference",
            content="User prefers Python over JavaScript",
            description="Language preference",
        )

        assert memory.user_id == "user_123"
        assert memory.project_path == "/my/project"
        assert memory.type == MemoryType.USER
        assert memory.name == "User Preference"
        assert memory.is_fresh is True
        assert memory.age_days == 0

    def test_memory_is_fresh(self):
        """测试记忆新鲜度"""
        # 创建一个刚更新的记忆
        fresh_memory = Memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.PROJECT,
            name="Fresh",
            content="Fresh content",
        )
        assert fresh_memory.is_fresh is True

    def test_update_content(self):
        """测试更新内容"""
        memory = Memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.FEEDBACK,
            name="Feedback",
            content="Original content",
        )

        original_updated = memory.updated_at

        # 更新内容
        import time
        time.sleep(0.01)  # 确保时间戳变化
        memory.update_content("Updated content")

        assert memory.content == "Updated content"
        assert memory.updated_at > original_updated

    def test_to_prompt_text(self):
        """测试转换为提示词文本"""
        memory = Memory(
            user_id="user_1",
            project_path="/project",
            type=MemoryType.REFERENCE,
            name="API Doc",
            content="API documentation is at /docs/api",
        )

        prompt_text = memory.to_prompt_text()
        assert "[reference]" in prompt_text
        assert "API Doc" in prompt_text
        assert "API documentation" in prompt_text
        assert "[fresh]" in prompt_text

    def test_memory_user_isolation(self):
        """测试多用户隔离 - 不同用户创建的记忆"""
        memory_user_a = Memory(
            user_id="user_a",
            project_path="/project",
            type=MemoryType.USER,
            name="Preference A",
            content="User A prefers dark mode",
        )

        memory_user_b = Memory(
            user_id="user_b",
            project_path="/project",
            type=MemoryType.USER,
            name="Preference B",
            content="User B prefers light mode",
        )

        assert memory_user_a.user_id != memory_user_b.user_id
        assert memory_user_a.user_id == "user_a"
        assert memory_user_b.user_id == "user_b"


class TestMemoryTypeScenarios:
    """测试四种记忆类型的场景"""

    def test_user_memory(self):
        """测试用户类型记忆"""
        memory = Memory(
            user_id="user_1",
            project_path="",
            type=MemoryType.USER,
            name="Role",
            content="User is a senior Python developer",
        )
        assert memory.type == MemoryType.USER

    def test_feedback_memory(self):
        """测试反馈类型记忆"""
        memory = Memory(
            user_id="user_1",
            project_path="/myapp",
            type=MemoryType.FEEDBACK,
            name="Code Style",
            content="Prefer type hints in all function signatures",
        )
        assert memory.type == MemoryType.FEEDBACK

    def test_project_memory(self):
        """测试项目类型记忆"""
        memory = Memory(
            user_id="user_1",
            project_path="/myapp",
            type=MemoryType.PROJECT,
            name="Deadline",
            content="Project deadline is 2026-12-31",
        )
        assert memory.type == MemoryType.PROJECT

    def test_reference_memory(self):
        """测试引用类型记忆"""
        memory = Memory(
            user_id="user_1",
            project_path="/myapp",
            type=MemoryType.REFERENCE,
            name="Architecture Doc",
            content="See /docs/architecture.md for system design",
        )
        assert memory.type == MemoryType.REFERENCE
