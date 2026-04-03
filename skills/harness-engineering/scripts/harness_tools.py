"""
Harness Engineering Skill - 工具脚本

提供任务初始化、质量检查、计划生成等功能。
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
HARNESS_DIR = PROJECT_ROOT / ".claude"


def run_init(task_description: str) -> str:
    """
    初始化任务上下文

    Args:
        task_description: 任务描述

    Returns:
        上下文信息文本
    """
    script_path = HARNESS_DIR / "context_initializer.py"
    if not script_path.exists():
        return f"错误: 未找到 {script_path}"

    try:
        result = subprocess.run(
            [sys.executable, str(script_path), task_description],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"执行失败: {e}"


def run_quality() -> str:
    """
    运行质量门禁检查

    Returns:
        检查结果文本
    """
    script_path = HARNESS_DIR / "hooks" / "quality-gates.sh"
    if not script_path.exists():
        return f"错误: 未找到 {script_path}"

    try:
        result = subprocess.run(
            ["bash", str(script_path)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"执行失败: {e}"


def run_audit(target: str = ".") -> str:
    """
    运行裸 JSON 审计

    Args:
        target: 审计目标路径，默认为当前目录

    Returns:
        审计结果文本
    """
    script_path = PROJECT_ROOT / "scripts" / "audit_bare_json.py"
    config_path = PROJECT_ROOT / ".bare-json-whitelist.json"

    if not script_path.exists():
        return f"错误: 未找到 {script_path}"

    try:
        cmd = [sys.executable, str(script_path)]
        if config_path.exists():
            cmd.extend(["--config", str(config_path)])
        cmd.append(target)

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT
        )
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return f"执行失败: {e}"


def run_plan(task_description: str) -> str:
    """
    生成任务执行计划（简化版）

    Args:
        task_description: 任务描述

    Returns:
        计划文本
    """
    # 检测任务类型
    task_lower = task_description.lower()

    task_type = "general"
    if any(k in task_lower for k in ["bug", "fix", "修复"]):
        task_type = "bugfix"
    elif any(k in task_lower for k in ["feature", "功能", "新增"]):
        task_type = "feature"
    elif any(k in task_lower for k in ["refactor", "重构"]):
        task_type = "refactor"
    elif any(k in task_lower for k in ["openspec", "spec", "规范"]):
        task_type = "openspec"

    # 生成建议的子任务
    subtasks = []
    if task_type == "bugfix":
        subtasks = [
            "[test] 复现 bug，添加失败测试用例",
            "[worker] 定位问题根因",
            "[worker] 修复 bug",
            "[test] 验证修复，确保测试通过",
            "[reviewer] 代码审查",
        ]
    elif task_type == "feature":
        subtasks = [
            "[model] 设计数据模型 (Pydantic)",
            "[backend] 实现核心业务逻辑",
            "[frontend] 实现用户界面",
            "[test] 添加单元测试",
            "[reviewer] 代码审查",
        ]
    elif task_type == "refactor":
        subtasks = [
            "[worker] 分析现有代码结构",
            "[worker] 执行重构 (保持行为不变)",
            "[test] 确保所有测试通过",
            "[reviewer] 代码审查",
        ]
    else:
        subtasks = [
            "[worker] 分析需求",
            "[worker] 实现功能",
            "[test] 添加测试",
            "[reviewer] 代码审查",
        ]

    output = f"""任务计划生成
================
原始任务: {task_description}
任务类型: {task_type}

建议执行步骤:
"""
    for i, task in enumerate(subtasks, 1):
        output += f"{i}. {task}\n"

    output += """
执行建议:
1. 按顺序完成每个子任务
2. 每个步骤完成后运行 /harness:quality 检查
3. 遇到阻塞及时反馈
"""

    return output


# Skill 工具注册接口
def tool_init(task_description: str) -> str:
    """Skill 工具: 初始化任务上下文"""
    return run_init(task_description)


def tool_quality() -> str:
    """Skill 工具: 运行质量门禁"""
    return run_quality()


def tool_audit(target: str = ".") -> str:
    """Skill 工具: 裸 JSON 审计"""
    return run_audit(target)


def tool_plan(task_description: str) -> str:
    """Skill 工具: 生成任务计划"""
    return run_plan(task_description)


if __name__ == "__main__":
    # 命令行入口
    if len(sys.argv) < 2:
        print("用法: python harness_tools.py <command> [args]")
        print("命令: init, quality, audit, plan")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "init" and len(sys.argv) > 2:
        print(run_init(sys.argv[2]))
    elif cmd == "quality":
        print(run_quality())
    elif cmd == "audit":
        target = sys.argv[2] if len(sys.argv) > 2 else "."
        print(run_audit(target))
    elif cmd == "plan" and len(sys.argv) > 2:
        print(run_plan(sys.argv[2]))
    else:
        print(f"未知命令: {cmd}")
        sys.exit(1)
