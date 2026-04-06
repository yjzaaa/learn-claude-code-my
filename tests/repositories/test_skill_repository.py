"""
Tests for Skill Repository - 技能仓库测试
"""


import pytest

from backend.domain.models import Skill, SkillDefinition
from backend.domain.repositories.skill_repository import ISkillRepository
from backend.infrastructure.persistence.memory.skill_repo import InMemorySkillRepository


@pytest.fixture
def repo():
    """创建内存仓库实例"""
    return InMemorySkillRepository()


@pytest.fixture
def sample_skill():
    """创建示例技能"""
    definition = SkillDefinition(
        name="Test Skill",
        description="A test skill",
        version="1.0.0",
        author="Test Author"
    )
    return Skill(
        id="skill_test",
        definition=definition,
        path="/test/path",
        scripts_loaded=True
    )


class TestInMemorySkillRepository:
    """内存技能仓库测试类"""

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo: ISkillRepository, sample_skill: Skill):
        """测试保存和获取技能"""
        # 保存技能
        await repo.save(sample_skill)

        # 获取技能
        retrieved = await repo.get(sample_skill.id)

        # 验证
        assert retrieved is not None
        assert retrieved.id == sample_skill.id
        assert retrieved.name == "Test Skill"
        assert retrieved.definition.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, repo: ISkillRepository):
        """测试获取不存在的技能"""
        result = await repo.get("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_list_all(self, repo: ISkillRepository):
        """测试列出所有技能"""
        # 初始为空
        skills = await repo.list_all()
        assert len(skills) == 0

        # 添加两个技能
        def1 = SkillDefinition(name="Skill 1", description="First skill")
        def2 = SkillDefinition(name="Skill 2", description="Second skill")
        skill1 = Skill(id="skill_1", definition=def1)
        skill2 = Skill(id="skill_2", definition=def2)
        await repo.save(skill1)
        await repo.save(skill2)

        # 列出所有
        skills = await repo.list_all()
        assert len(skills) == 2
        assert {s.name for s in skills} == {"Skill 1", "Skill 2"}

    @pytest.mark.asyncio
    async def test_delete(self, repo: ISkillRepository, sample_skill: Skill):
        """测试删除技能"""
        # 保存并删除
        await repo.save(sample_skill)
        await repo.delete(sample_skill.id)

        # 验证已删除
        retrieved = await repo.get(sample_skill.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, repo: ISkillRepository):
        """测试删除不存在的技能（不应抛出异常）"""
        # 不应抛出异常
        await repo.delete("nonexistent-id")

    @pytest.mark.asyncio
    async def test_update_existing(self, repo: ISkillRepository, sample_skill: Skill):
        """测试更新已存在的技能"""
        # 保存初始版本
        await repo.save(sample_skill)

        # 修改技能
        sample_skill.scripts_loaded = False
        await repo.save(sample_skill)

        # 验证更新
        retrieved = await repo.get(sample_skill.id)
        assert retrieved is not None
        assert retrieved.scripts_loaded is False

    @pytest.mark.asyncio
    async def test_clear(self, repo: InMemorySkillRepository):
        """测试清空所有技能"""
        # 添加技能
        definition = SkillDefinition(name="Test", description="Test skill")
        skill = Skill(id="test", definition=definition)
        await repo.save(skill)
        assert repo.count() == 1

        # 清空
        repo.clear()
        assert repo.count() == 0
        assert len(await repo.list_all()) == 0


class TestSkillRepositoryInterface:
    """测试仓库接口契约"""

    def test_is_abstract(self):
        """测试 ISkillRepository 是抽象类"""
        with pytest.raises(TypeError):
            ISkillRepository()

    def test_inmemory_implements_interface(self):
        """测试 InMemorySkillRepository 实现接口"""
        assert issubclass(InMemorySkillRepository, ISkillRepository)
