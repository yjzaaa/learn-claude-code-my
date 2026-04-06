"""
简单的提示词工具 - 从 .env 加载配置并生成公共提示词
"""
import os

from dotenv import load_dotenv

load_dotenv(override=True)


def _get_env_list(key: str, default: str = "") -> list[str]:
    """从环境变量获取逗号分隔的列表"""
    value = os.getenv(key, default)
    return [item.strip() for item in value.split(",") if item.strip()] if value else []


def get_security_prompt() -> str:
    """获取安全策略提示词（从 .env 加载）"""
    blacklist_cmds = _get_env_list("AGENT_BLACKLIST_COMMANDS")
    blacklist_paths = _get_env_list("AGENT_BLACKLIST_PATHS")
    whitelist_cmds = _get_env_list("AGENT_WHITELIST_COMMANDS")

    lines = ["## 安全策略", ""]

    if blacklist_cmds:
        lines.extend(["### 禁止执行以下命令：", ""])
        for cmd in blacklist_cmds:
            lines.append(f"- 禁止: `{cmd}`")
        lines.append("")

    if blacklist_paths:
        lines.extend(["### 禁止访问以下路径：", ""])
        for path in blacklist_paths:
            lines.append(f"- 禁止: `{path}`")
        lines.append("")

    if whitelist_cmds:
        lines.extend(["### 允许执行的命令：", ""])
        for cmd in whitelist_cmds:
            lines.append(f"- 允许: `{cmd}`")
        lines.append("")

    return "\n".join(lines)


# 公共提示词片段（所有 agent 共享）
BASE_PROMPT = f"""
{get_security_prompt()}

### 基本行为准则
1. 绝不执行黑名单中的危险操作
2. 敏感文件访问前必须确认
3. 生产环境操作需要二次确认
4. 工具调用前说明意图
5. 操作完成后报告结果
"""


def with_base_prompt(system_prompt: str) -> str:
    """将公共提示词嵌入到 agent 的 system prompt 中"""
    return f"{system_prompt}\n\n{BASE_PROMPT}"
