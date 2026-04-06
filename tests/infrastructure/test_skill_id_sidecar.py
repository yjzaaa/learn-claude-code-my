"""
Tests for Skill ID Sidecar

测试技能 ID sidecar 的创建、读取和持久化功能。
"""

import tempfile
from pathlib import Path

import pytest

from backend.domain.models.agent.skill_engine_types import SkillOrigin
from backend.infrastructure.services.skill_id_sidecar import (
    SIDECAR_FILENAME,
    _generate_skill_id,
    _generate_uuid8,
    _read_or_create_skill_id,
    generate_evolved_skill_id,
    parse_skill_id,
    read_skill_id,
    write_skill_id,
)


class TestGenerateUUID8:
    """测试 UUID8 生成"""

    def test_length_is_8(self):
        """生成的 UUID 应该是 8 字符"""
        uuid8 = _generate_uuid8()
        assert len(uuid8) == 8

    def test_is_hex(self):
        """生成的 UUID 应该是十六进制字符"""
        uuid8 = _generate_uuid8()
        assert all(c in "0123456789abcdef" for c in uuid8)

    def test_uniqueness(self):
        """多次生成应该产生不同值"""
        uuids = {_generate_uuid8() for _ in range(100)}
        assert len(uuids) == 100


class TestGenerateSkillID:
    """测试技能 ID 生成"""

    def test_imported_format(self):
        """导入技能格式: name__imp_{uuid8}"""
        skill_id = _generate_skill_id("finance", SkillOrigin.IMPORTED)
        assert skill_id.startswith("finance__imp_")
        assert len(skill_id.split("__imp_")[1]) == 8

    def test_evolved_format(self):
        """进化技能格式: name__v{gen}_{uuid8}"""
        skill_id = _generate_skill_id("finance", SkillOrigin.EVOLVED, generation=2)
        assert skill_id.startswith("finance__v2_")
        assert len(skill_id.split("__v2_")[1]) == 8

    def test_different_generations(self):
        """不同代数应该产生不同格式"""
        v1 = _generate_skill_id("test", SkillOrigin.EVOLVED, 1)
        v2 = _generate_skill_id("test", SkillOrigin.EVOLVED, 2)
        v3 = _generate_skill_id("test", SkillOrigin.EVOLVED, 3)

        assert "__v1_" in v1
        assert "__v2_" in v2
        assert "__v3_" in v3

    def test_name_with_hyphen(self):
        """支持带连字符的名称"""
        skill_id = _generate_skill_id("data-analysis", SkillOrigin.IMPORTED)
        assert skill_id.startswith("data-analysis__imp_")


class TestReadOrCreateSkillID:
    """测试读取或创建技能 ID"""

    def test_creates_new_when_not_exists(self):
        """当 sidecar 不存在时创建新 ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            skill_id, is_new = _read_or_create_skill_id(skill_dir, "test-skill")

            assert is_new is True
            assert skill_id.startswith("test-skill__imp_")

            # 验证文件已创建
            sidecar = skill_dir / SIDECAR_FILENAME
            assert sidecar.exists()
            assert sidecar.read_text().strip() == skill_id

    def test_reads_existing(self):
        """当 sidecar 存在时读取现有 ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            existing_id = "my-skill__imp_a1b2c3d4"

            # 预先创建 sidecar
            sidecar = skill_dir / SIDECAR_FILENAME
            sidecar.write_text(existing_id + "\n")

            skill_id, is_new = _read_or_create_skill_id(skill_dir, "my-skill")

            assert is_new is False
            assert skill_id == existing_id

    def test_regenerates_on_invalid_format(self):
        """格式无效时重新生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)

            # 写入无效内容
            sidecar = skill_dir / SIDECAR_FILENAME
            sidecar.write_text("invalid-content\n")

            skill_id, is_new = _read_or_create_skill_id(skill_dir, "test")

            assert is_new is True
            assert "__imp_" in skill_id

    def test_handles_read_permission_error(self):
        """处理读取权限错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            sidecar = skill_dir / SIDECAR_FILENAME
            sidecar.write_text("test__imp_12345678\n")

            # 移除读权限
            sidecar.chmod(0o000)
            try:
                skill_id, is_new = _read_or_create_skill_id(skill_dir, "test")
                # 应该生成新 ID（内存中）
                assert is_new is True
                assert skill_id.startswith("test__imp_")
            finally:
                sidecar.chmod(0o644)

    def test_handles_write_permission_error(self):
        """处理写入权限错误"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            # 移除目录写权限
            skill_dir.chmod(0o555)
            try:
                skill_id, is_new = _read_or_create_skill_id(skill_dir, "test")
                # 应该生成 ID 但不写入文件
                assert skill_id.startswith("test__imp_")
            finally:
                skill_dir.chmod(0o755)


class TestReadSkillID:
    """测试读取技能 ID"""

    def test_returns_none_when_not_exists(self):
        """文件不存在时返回 None"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = read_skill_id(Path(tmpdir))
            assert result is None

    def test_returns_content_when_exists(self):
        """文件存在时返回内容"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            sidecar = skill_dir / SIDECAR_FILENAME
            sidecar.write_text("my-id__imp_12345678\n")

            result = read_skill_id(skill_dir)
            assert result == "my-id__imp_12345678"


class TestWriteSkillID:
    """测试写入技能 ID"""

    def test_writes_correctly(self):
        """正确写入技能 ID"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            result = write_skill_id(skill_dir, "test__imp_abcdef12")

            assert result is True
            sidecar = skill_dir / SIDECAR_FILENAME
            assert sidecar.read_text().strip() == "test__imp_abcdef12"

    def test_returns_false_on_permission_error(self):
        """权限错误时返回 False"""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir)
            skill_dir.chmod(0o555)
            try:
                result = write_skill_id(skill_dir, "test__imp_abcdef12")
                assert result is False
            finally:
                skill_dir.chmod(0o755)


class TestGenerateEvolvedSkillID:
    """测试进化技能 ID 生成"""

    def test_increments_generation(self):
        """代数自动递增"""
        from backend.domain.models.agent.skill_engine_types import SkillMeta

        parent = SkillMeta(
            skill_id="finance__imp_a1b2c3d4",
            name="finance",
            origin=SkillOrigin.IMPORTED,
            generation=1,
        )

        new_id = generate_evolved_skill_id(parent)
        assert "__v2_" in new_id

    def test_uses_specified_generation(self):
        """使用指定的代数"""
        from backend.domain.models.agent.skill_engine_types import SkillMeta

        parent = SkillMeta(
            skill_id="finance__v2_a1b2c3d4",
            name="finance",
            origin=SkillOrigin.EVOLVED,
            generation=2,
        )

        new_id = generate_evolved_skill_id(parent, new_generation=5)
        assert "__v5_" in new_id


class TestParseSkillID:
    """测试技能 ID 解析"""

    def test_parse_imported(self):
        """解析导入技能 ID"""
        result = parse_skill_id("finance__imp_a1b2c3d4")
        assert result == ("finance", "imported", 1)

    def test_parse_evolved(self):
        """解析进化技能 ID"""
        result = parse_skill_id("finance__v3_b2c3d4e5")
        assert result == ("finance", "evolved", 3)

    def test_parse_invalid(self):
        """解析无效 ID"""
        result = parse_skill_id("invalid-id")
        assert result is None

    def test_parse_empty(self):
        """解析空字符串"""
        result = parse_skill_id("")
        assert result is None
