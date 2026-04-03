"""
Tests for Dialog Repository - 对话仓库测试
"""

import pytest
import asyncio

from core.domain.repositories.dialog_repository import IDialogRepository
from core.infrastructure.persistence.memory.dialog_repo import InMemoryDialogRepository
from core.models.entities import Dialog, Message


@pytest.fixture
def repo():
    """创建内存仓库实例"""
    return InMemoryDialogRepository()


@pytest.fixture
def sample_dialog():
    """创建示例对话"""
    dialog = Dialog.create(title="Test Dialog")
    dialog.add_message(Message.user("Hello"))
    dialog.add_message(Message.assistant("Hi there!"))
    return dialog


class TestInMemoryDialogRepository:
    """内存对话仓库测试类"""

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo: IDialogRepository, sample_dialog: Dialog):
        """测试保存和获取对话"""
        # 保存对话
        await repo.save(sample_dialog)

        # 获取对话
        retrieved = await repo.get(sample_dialog.id)

        # 验证
        assert retrieved is not None
        assert retrieved.id == sample_dialog.id
        assert retrieved.title == sample_dialog.title
        assert len(retrieved.messages) == 2

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, repo: IDialogRepository):
        """测试获取不存在的对话"""
        result = await repo.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self, repo: IDialogRepository):
        """测试列出所有对话"""
        # 初始为空
        dialogs = await repo.list_all()
        assert len(dialogs) == 0

        # 添加两个对话
        dialog1 = Dialog.create(title="Dialog 1")
        dialog2 = Dialog.create(title="Dialog 2")
        await repo.save(dialog1)
        await repo.save(dialog2)

        # 列出所有
        dialogs = await repo.list_all()
        assert len(dialogs) == 2
        assert {d.title for d in dialogs} == {"Dialog 1", "Dialog 2"}

    @pytest.mark.asyncio
    async def test_delete(self, repo: IDialogRepository, sample_dialog: Dialog):
        """测试删除对话"""
        # 保存并删除
        await repo.save(sample_dialog)
        await repo.delete(sample_dialog.id)

        # 验证已删除
        retrieved = await repo.get(sample_dialog.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo: IDialogRepository):
        """测试删除不存在的对话（不应抛出异常）"""
        # 不应抛出异常
        await repo.delete("nonexistent-id")

    @pytest.mark.asyncio
    async def test_update_existing(self, repo: IDialogRepository, sample_dialog: Dialog):
        """测试更新已存在的对话"""
        # 保存初始版本
        await repo.save(sample_dialog)

        # 修改对话
        sample_dialog.add_message(Message.user("New message"))
        await repo.save(sample_dialog)

        # 验证更新
        retrieved = await repo.get(sample_dialog.id)
        assert retrieved is not None
        assert len(retrieved.messages) == 3

    @pytest.mark.asyncio
    async def test_clear(self, repo: InMemoryDialogRepository):
        """测试清空所有对话"""
        # 添加对话
        dialog = Dialog.create(title="Test")
        await repo.save(dialog)
        assert repo.count() == 1

        # 清空
        repo.clear()
        assert repo.count() == 0
        assert len(await repo.list_all()) == 0


class TestDialogRepositoryInterface:
    """测试仓库接口契约"""

    def test_is_abstract(self):
        """测试 IDialogRepository 是抽象类"""
        with pytest.raises(TypeError):
            IDialogRepository()

    def test_inmemory_implements_interface(self):
        """测试 InMemoryDialogRepository 实现接口"""
        assert issubclass(InMemoryDialogRepository, IDialogRepository)
