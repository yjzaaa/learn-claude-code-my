"""
Test Backend-Aware Prompt Injection - 后端感知提示词注入测试

测试 Backend-Aware Prompt Injection 功能，包括：
- 后端检测
- 提示词构建
- {baseDir} 占位符替换
- 完整注入流程
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))


def test_backend_hints():
    """测试后端提示词定义"""
    print("\n=== Test Backend Hints ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        BACKEND_HINTS,
    )

    # Verify all expected backends are defined
    expected_backends = ["shell", "mcp", "gui", "docker", "browser", "database"]
    for backend in expected_backends:
        assert backend in BACKEND_HINTS
        assert len(BACKEND_HINTS[backend]) > 0
        print(f"✓ Backend hint for '{backend}' defined")


def test_resource_access_tips():
    """测试资源访问提示"""
    print("\n=== Test Resource Access Tips ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        RESOURCE_ACCESS_TIPS,
    )

    # Verify tips contain expected content
    assert "read_file" in RESOURCE_ACCESS_TIPS
    assert "write_file" in RESOURCE_ACCESS_TIPS
    assert "list_dir" in RESOURCE_ACCESS_TIPS
    assert "skill directory" in RESOURCE_ACCESS_TIPS
    print("✓ Resource access tips contain expected content")


def test_get_available_backends():
    """测试获取可用后端"""
    print("\n=== Test Get Available Backends ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        SkillEngineMiddleware,
    )

    # Create mock skill manager
    mock_skill_manager = MagicMock()
    mock_skill_manager.get_active_tools.return_value = [
        MagicMock(tool={"name": "shell_execute"}),
        MagicMock(tool={"name": "mcp_call"}),
        MagicMock(tool={"name": "docker_run"}),
    ]

    middleware = SkillEngineMiddleware(skill_manager=mock_skill_manager)

    backends = middleware._get_available_backends()

    assert "shell" in backends
    assert "mcp" in backends
    assert "docker" in backends
    print(f"✓ Detected backends: {backends}")


def test_build_backend_hint():
    """测试构建后端提示词"""
    print("\n=== Test Build Backend Hint ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        SkillEngineMiddleware,
    )

    mock_skill_manager = MagicMock()
    middleware = SkillEngineMiddleware(skill_manager=mock_skill_manager)

    # Test with specific backends
    hint = middleware._build_backend_hint(["shell", "mcp"])
    assert "Available Tools" in hint
    assert "shell" in hint.lower()
    assert "mcp" in hint.lower()
    assert "gui" not in hint.lower()
    print("✓ Backend hint built correctly for shell, mcp")

    # Test with empty backends
    hint = middleware._build_backend_hint([])
    assert hint == ""
    print("✓ Empty backends returns empty hint")


def test_replace_basedir_placeholder():
    """测试 {baseDir} 占位符替换"""
    print("\n=== Test Replace {baseDir} Placeholder ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        SkillEngineMiddleware,
    )

    mock_skill_manager = MagicMock()
    middleware = SkillEngineMiddleware(skill_manager=mock_skill_manager)

    # Test with placeholder
    content = "See {baseDir}/scripts/helper.py for details"
    skill_path = "/path/to/skills/finance"
    result = middleware._replace_basedir_placeholder(content, skill_path)
    assert "/path/to/skills/finance/scripts/helper.py" in result
    assert "{baseDir}" not in result
    print("✓ {baseDir} replaced with absolute path")

    # Test without placeholder
    content = "See scripts/helper.py for details"
    result = middleware._replace_basedir_placeholder(content, skill_path)
    assert result == content
    print("✓ Content without placeholder unchanged")

    # Test with None skill_path
    content = "See {baseDir}/scripts/helper.py"
    result = middleware._replace_basedir_placeholder(content, None)
    assert result == content
    print("✓ None skill_path returns original content")


def test_build_skill_section():
    """测试构建技能部分"""
    print("\n=== Test Build Skill Section ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        SkillEngineMiddleware,
    )

    # Create mock skill
    mock_skill = MagicMock()
    mock_skill.id = "finance__imp_a3f2b1c9"
    mock_skill.definition.name = "finance"
    mock_skill.path = "/path/to/skills/finance"

    mock_ranked = MagicMock()
    mock_ranked.skill = mock_skill

    mock_skill_manager = MagicMock()
    mock_skill_manager.get_skill_prompt.return_value = "Financial analysis skill content"

    middleware = SkillEngineMiddleware(skill_manager=mock_skill_manager)

    section = middleware._build_skill_section(mock_ranked)

    assert "### Skill: finance__imp_a3f2b1c9" in section
    assert "Skill directory" in section
    assert "/path/to/skills/finance" in section
    assert "Financial analysis skill content" in section
    print("✓ Skill section built correctly")


def test_build_context_injection():
    """测试构建完整上下文注入"""
    print("\n=== Test Build Context Injection ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        SkillEngineMiddleware,
    )

    # Create mock skills
    mock_skill1 = MagicMock()
    mock_skill1.id = "skill_1"
    mock_skill1.definition.name = "Skill 1"
    mock_skill1.path = "/path/to/skill1"

    mock_skill2 = MagicMock()
    mock_skill2.id = "skill_2"
    mock_skill2.definition.name = "Skill 2"
    mock_skill2.path = "/path/to/skill2"

    mock_ranked1 = MagicMock()
    mock_ranked1.skill = mock_skill1

    mock_ranked2 = MagicMock()
    mock_ranked2.skill = mock_skill2

    mock_skill_manager = MagicMock()
    mock_skill_manager.get_skill_prompt.side_effect = [
        "Skill 1 content",
        "Skill 2 content",
    ]

    middleware = SkillEngineMiddleware(skill_manager=mock_skill_manager)

    injection = middleware._build_context_injection(
        [mock_ranked1, mock_ranked2],
        backends=["shell", "mcp"],
    )

    # Verify header
    assert "# Active Skills" in injection
    assert "## How to use skills" in injection

    # Verify backend hints
    assert "## Available Tools" in injection
    assert "shell" in injection.lower()

    # Verify resource tips
    assert "read_file" in injection
    assert "skill directory" in injection

    # Verify skills are included
    assert "### Skill: skill_1" in injection
    assert "### Skill: skill_2" in injection
    assert "---" in injection  # Separator

    print("✓ Context injection built correctly")


def test_empty_skills():
    """测试空技能列表"""
    print("\n=== Test Empty Skills ===")

    from backend.infrastructure.runtime.deep.middleware.skill_engine import (
        SkillEngineMiddleware,
    )

    mock_skill_manager = MagicMock()
    middleware = SkillEngineMiddleware(skill_manager=mock_skill_manager)

    injection = middleware._build_context_injection([], backends=["shell"])
    assert injection == ""
    print("✓ Empty skills returns empty injection")


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("Backend-Aware Prompt Injection Tests")
    print("=" * 60)

    test_backend_hints()
    test_resource_access_tips()
    test_get_available_backends()
    test_build_backend_hint()
    test_replace_basedir_placeholder()
    test_build_skill_section()
    test_build_context_injection()
    test_empty_skills()

    print("\n" + "=" * 60)
    print("All Backend-Aware Prompt Injection tests passed! ✓")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
