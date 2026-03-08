"""
PluginEnabledAgent - 带插件支持的 Agent 基类

封装所有插件基础设施，让具体 Agent 只关注业务逻辑。
"""

from typing import Any, Callable, Dict, List, Optional, Type

from .base_agent_loop import BaseAgentLoop
from .toolkit import build_tools_and_handlers

try:
    from ..plugins import PluginManager, AgentPlugin
    from ..providers import create_provider_from_env
except ImportError:
    from agents.plugins import PluginManager, AgentPlugin
    from agents.providers import create_provider_from_env


def _get_default_plugins():
    """延迟导入默认插件，避免循环导入"""
    try:
        from ..plugins.skill_plugin import SkillPlugin
        from ..plugins.compact_plugin import CompactPlugin
    except ImportError:
        from agents.plugins.skill_plugin import SkillPlugin
        from agents.plugins.compact_plugin import CompactPlugin
    return [SkillPlugin, CompactPlugin]


class PluginEnabledAgent(BaseAgentLoop):
    """
    带插件支持的 Agent 基类 - 可继承

    封装了插件管理的所有基础设施：
    - PluginManager 初始化
    - 插件注册（包括默认插件）
    - 钩子函数包装
    - 工具合并
    - 系统提示词组合

    子类只需：
    1. 定义 _default_plugins 类属性指定默认插件
    2. 提供基础系统提示词和工具

    示例:
        class MyAgent(PluginEnabledAgent):
            _default_plugins = [SkillPlugin, CompactPlugin]

            def __init__(self, **kwargs):
                super().__init__(
                    system="You are helpful",
                    tools=[my_tool],
                    **kwargs
                )
    """

    # 默认插件：技能加载 + 上下文压缩
    # 子类可覆盖此属性指定不同的默认插件，或覆盖 _get_default_plugins() 方法
    _default_plugins: Optional[List[Type[AgentPlugin]]] = None

    def __init__(
        self,
        # 基础配置
        system: str = "",
        tools: Optional[List[Callable]] = None,
        tool_handlers: Optional[Dict[str, Callable]] = None,
        # 插件配置
        plugins: Optional[List[Type[AgentPlugin]]] = None,
        enable_default_plugins: bool = False,
        # BaseAgentLoop 配置
        provider=None,
        model: Optional[str] = None,
        max_tokens: int = 8000,
        max_rounds: int = 25,
        # 钩子（会被包装以支持插件）
        **kwargs
    ):
        # 1. 初始化插件管理器
        self.plugin_manager = PluginManager(self)

        # 2. 注册默认插件（从类属性或覆盖方法）
        if enable_default_plugins:
            default_plugins = self._get_default_plugins()
            for plugin_class in default_plugins:
                self.plugin_manager.register(plugin_class)

        # 3. 注册用户指定的插件
        if plugins:
            self.plugin_manager.register_multiple(plugins)

        # 4. 构建工具：基础工具 + 插件工具
        base_tools = list(tools) if tools else []
        plugin_tools = self.plugin_manager.get_all_tools()
        all_tools = base_tools + plugin_tools

        # 5. 合并工具处理器
        base_handlers = dict(tool_handlers) if tool_handlers else {}
        plugin_handlers = self.plugin_manager.get_all_tool_handlers()
        all_handlers = {**base_handlers, **plugin_handlers}

        # 6. 包装工具处理器以支持 on_tool_result
        wrapped_handlers = {
            name: self._wrap_handler(name, handler)
            for name, handler in all_handlers.items()
        }

        # 7. 构建最终系统提示词
        final_system = self._build_system_prompt(system)

        # 8. 包装钩子函数
        wrapped_hooks = self._wrap_hooks(kwargs)

        # 9. 初始化 BaseAgentLoop
        super().__init__(
            provider=provider or create_provider_from_env(),
            model=model,
            system=final_system,
            tools=all_tools,
            tool_handlers=wrapped_handlers,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            **wrapped_hooks
        )

    def _get_default_plugins(self) -> List[Type[AgentPlugin]]:
        """
        获取默认插件列表

        子类可通过以下方式指定默认插件：
        1. 定义 _default_plugins 类属性
        2. 覆盖此方法动态返回插件列表

        基类默认返回 [SkillPlugin, CompactPlugin]

        Returns:
            默认插件类列表
        """
        if self._default_plugins:
            return self._default_plugins
        # 延迟导入默认插件，避免循环导入
        return _get_default_plugins()

    def _build_system_prompt(self, base_system: str) -> str:
        """
        构建最终系统提示词

        基础提示词 + 插件追加内容
        """
        plugin_addon = self.plugin_manager.get_combined_system_prompt()
        if plugin_addon:
            return f"{base_system}\n{plugin_addon}"
        return base_system

    def _wrap_handler(self, name: str, handler: Callable) -> Callable:
        """
        包装工具处理器，添加插件支持

        在调用原始处理器后，触发插件的 on_tool_result
        """
        def wrapped_handler(**kwargs):
            result = handler(**kwargs)
            self.plugin_manager.on_tool_result(name, str(result))
            return result
        return wrapped_handler

    def _wrap_hooks(self, kwargs: Dict) -> Dict:
        """
        包装钩子函数，添加插件支持

        在调用原始钩子前后，触发对应的插件方法
        """
        original_hooks = kwargs.copy()
        wrapped = {}

        # stream_token 钩子
        if "on_stream_token" in original_hooks:
            orig = original_hooks["on_stream_token"]
            def wrapped_on_stream_token(chunk, _orig=orig, _self=self):
                _self.plugin_manager.on_stream_token(chunk)
                try:
                    _orig(chunk)
                except Exception:
                    pass
            wrapped["on_stream_token"] = wrapped_on_stream_token
        else:
            wrapped["on_stream_token"] = self.plugin_manager.on_stream_token

        # tool_call 钩子
        if "on_tool_call" in original_hooks:
            orig = original_hooks["on_tool_call"]
            def wrapped_on_tool_call(name: str, arguments: dict, _orig=orig, _self=self):
                _self.plugin_manager.on_tool_call(name, arguments)
                try:
                    _orig(name, arguments)
                except Exception:
                    pass
            wrapped["on_tool_call"] = wrapped_on_tool_call
        else:
            wrapped["on_tool_call"] = self.plugin_manager.on_tool_call

        # complete 钩子
        if "on_complete" in original_hooks:
            orig = original_hooks["on_complete"]
            def wrapped_on_complete(content: str, _orig=orig, _self=self):
                _self.plugin_manager.on_complete(content)
                try:
                    _orig(content)
                except Exception:
                    pass
            wrapped["on_complete"] = wrapped_on_complete
        else:
            wrapped["on_complete"] = self.plugin_manager.on_complete

        # error 钩子
        if "on_error" in original_hooks:
            orig = original_hooks["on_error"]
            def wrapped_on_error(error: Exception, _orig=orig, _self=self):
                _self.plugin_manager.on_error(error)
                try:
                    _orig(error)
                except Exception:
                    pass
            wrapped["on_error"] = wrapped_on_error
        else:
            wrapped["on_error"] = self.plugin_manager.on_error

        # stop 钩子
        if "on_stop" in original_hooks:
            orig = original_hooks["on_stop"]
            def wrapped_on_stop(_orig=orig, _self=self):
                _self.plugin_manager.on_stop()
                try:
                    _orig()
                except Exception:
                    pass
            wrapped["on_stop"] = wrapped_on_stop
        else:
            wrapped["on_stop"] = self.plugin_manager.on_stop

        return wrapped

    def run_with_plugins(self, messages: List[Dict]) -> str:
        """
        运行 Agent（带插件支持）

        在运行前调用插件的 on_before_run
        """
        # 插件：运行前处理
        self.plugin_manager.on_before_run(messages)

        # 运行代理循环
        return self.run(messages)


__all__ = ["PluginEnabledAgent"]
