"""
MemoryMiddleware 使用示例

展示如何在 AgentBuilder 中启用 MemoryMiddleware。
"""

from backend.infrastructure.runtime.deep.agent_builder import AgentBuilder


def example_basic_usage():
    """基础用法示例"""
    # 创建 AgentBuilder 实例
    builder = AgentBuilder()

    # 配置 Agent 基本参数
    builder.with_name("my-agent").with_model(my_model).with_tools(my_tools).with_system_prompt(
        "You are a helpful assistant."
    )

    # 启用记忆中间件
    builder.with_memory(
        user_id="user_123",  # 当前用户ID，用于数据隔离
        project_path="/workspace/my-project",  # 项目路径，用于作用域隔离
        db_session_factory=get_db_session,  # 数据库会话工厂
        auto_extract=True,  # 自动提取新记忆（默认True）
    )

    # 构建 Agent
    agent = builder.build()

    return agent


def example_with_other_middleware():
    """与其他中间件一起使用的示例"""
    builder = (
        AgentBuilder()
        .with_name("advanced-agent")
        .with_model(my_model)
        .with_tools(my_tools)
        .with_system_prompt("You are a helpful assistant.")
        .with_backend(my_backend)
        # 启用待办事项中间件
        .with_todo_list()
        # 启用文件系统中间件
        .with_filesystem()
        # 启用记忆中间件（建议在 TodoList 之后、Skills 之前）
        .with_memory(
            user_id="user_123",
            project_path="/workspace/my-project",
            db_session_factory=get_db_session,
            auto_extract=True,
        )
        # 启用技能中间件
        .with_skills(["finance", "coding"])
        # 启用 Claude 压缩中间件
        .with_claude_compression(level="standard", enable_session_memory=True)
        # 启用提示缓存
        .with_prompt_caching()
    )

    agent = builder.build()
    return agent


def example_factory_pattern():
    """使用 AgentFactory 的示例（推荐）"""
    from backend.infrastructure.runtime.deep.core.agent_factory import (
        AgentBuildContext,
        AgentFactory,
    )

    # 创建构建上下文
    context = AgentBuildContext(
        agent_id="my-agent",
        name="My Agent",
        model=my_model,
        tools=my_tools,
        system_prompt="You are a helpful assistant.",
        backend=my_backend,
        checkpointer=my_checkpointer,
        store=my_store,
        skills=["finance"],
    )

    # 注意：如果要使用 MemoryMiddleware，需要直接使用 AgentBuilder
    # AgentFactory 目前不直接支持 MemoryMiddleware，可以扩展 AgentBuildContext

    # 或者手动构建
    from backend.infrastructure.runtime.deep.agent_builder import AgentBuilder

    builder = (
        AgentBuilder()
        .with_name(context.name or context.agent_id)
        .with_model(context.model)
        .with_tools(context.tools)
        .with_system_prompt(context.system_prompt)
        .with_backend(context.backend)
        .with_checkpointer(context.checkpointer)
        .with_store(context.store)
        .with_skills(context.skills)
        .with_todo_list()
        .with_filesystem()
        # 添加记忆中间件
        .with_memory(
            user_id="user_123",
            project_path="/workspace/my-project",
            db_session_factory=get_db_session,
        )
        .with_claude_compression(level="standard", enable_session_memory=True)
        .with_prompt_caching()
    )

    agent = builder.build()
    return agent


# 模拟依赖（实际使用时需要真实实现）
my_model = None
my_tools = []
my_backend = None
my_checkpointer = None
my_store = None


def get_db_session():
    """数据库会话工厂示例"""
    # 返回一个异步数据库会话
    pass


if __name__ == "__main__":
    print("MemoryMiddleware 使用示例")
    print("=" * 50)
    print("\n1. 基础用法：")
    print("   builder.with_memory(user_id, project_path, db_session_factory)")
    print("\n2. 关键参数：")
    print("   - user_id: 用户ID，用于数据隔离")
    print("   - project_path: 项目路径，用于作用域隔离")
    print("   - db_session_factory: 数据库会话工厂")
    print("   - auto_extract: 是否自动提取新记忆（默认True）")
    print("\n3. 工作原理：")
    print("   - abefore_model: 在模型调用前加载相关记忆并注入系统提示词")
    print("   - aafter_model: 在响应后异步提取新记忆")
    print("\n4. 测试验证：")
    print("   运行: pytest tests/infrastructure/test_memory_middleware_agent_builder.py -v")
