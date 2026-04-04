"""
Backend - 后端核心模块

使用示例:
    from backend.application.engine import AgentEngine

    engine = AgentEngine(config)
    await engine.startup()
    dialog_id = await engine.create_dialog("Hello")
"""

__version__ = "0.2.0"

# 注意：为了避免循环导入，具体类型请从子模块导入
# 例如:
#   from backend.domain.models.shared.types import AgentStatus
#   from backend.application.services.todo import todo_store
