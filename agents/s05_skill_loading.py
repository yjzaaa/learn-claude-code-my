from loguru import logger
#!/usr/bin/env python3
"""
s05_skill_loading.py - 技能加载

两层技能注入机制，避免 system prompt 过度膨胀：

    第 1 层（低成本）：在 system prompt 中放技能名（约 100 tokens/技能）
    第 2 层（按需加载）：在 tool_result 中返回完整技能正文

    skills/
      pdf/
        SKILL.md          <-- frontmatter（name, description）+ 正文
      code-review/
        SKILL.md

    System prompt：
    +--------------------------------------+
    | You are a coding agent.              |
    | Skills available:                    |
    |   - pdf: Process PDF files...        |  <-- 第 1 层：仅元数据
    |   - code-review: Review code...      |
    +--------------------------------------+ba

    当模型调用 load_skill("pdf") 时：
    +--------------------------------------+
    | tool_result:                         |
    | <skill>                              |
    |   Full PDF processing instructions   |  <-- 第 2 层：完整正文
    |   Step 1: ...                        |
    |   Step 2: ...                        |
    | </skill>                             |
    +--------------------------------------+

关键点："不要把所有内容都塞进 system prompt，应按需加载。"
"""

import os
import re
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
try:
    from agents.providers import create_provider_from_env
except ImportError:
    from providers import create_provider_from_env
try:
    # 直接运行脚本：python agents/s05_skill_loading.py
    from base import WorkspaceOps, BaseAgentLoop, tool
except ImportError:
    # 作为包运行：python -m agents.s05_skill_loading
    from agents.base import WorkspaceOps, BaseAgentLoop, tool
WORKDIR = Path.cwd()
LOG_DIR = WORKDIR / ".logs"
LOG_FILE = LOG_DIR / "s05_messages.jsonl"
load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
SKILLS_DIR = WORKDIR / "skills"
OPS = WorkspaceOps(WORKDIR)

def read_text_safe(path: Path) -> str:
    """显式尝试多种编码读取文本，避免 Windows 本地编码解码失败。"""
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    # 最终兜底：对混合编码文件用替换策略，保证流程不中断。
    return path.read_text(encoding="utf-8", errors="replace")


# -- SkillLoader：扫描 skills/<name>/SKILL.md 并解析 frontmatter --
class SkillLoader:
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills = {}
        self.backups_dir = WORKDIR / ".backups" / "skills"
        self._load_all()

    def _load_all(self):
        if not self.skills_dir.exists():
            return
        for f in sorted(self.skills_dir.rglob("SKILL.md")):
            text = read_text_safe(f)
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {"meta": meta, "body": body, "path": str(f)}

    def _parse_frontmatter(self, text: str) -> tuple:
        """解析 --- 分隔的 YAML frontmatter。"""
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        meta = {}
        for line in match.group(1).strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        """第 1 层：返回 system prompt 使用的技能简要描述。"""
        if not self.skills:
            return "(no skills available)"
        lines = []
        for name, skill in self.skills.items():
            desc = skill["meta"].get("description", "No description")
            tags = skill["meta"].get("tags", "")
            line = f"  - {name}: {desc}"
            if tags:
                line += f" [{tags}]"
            lines.append(line)
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        """第 2 层：返回 tool_result 使用的完整技能正文。"""
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"

        refs_list = []
        scripts_list = []
        skill_dir = Path(skill["path"]).parent
        refs_dir = skill_dir / "references"
        scripts_dir = skill_dir / "scripts"

        if refs_dir.exists():
            refs_list = sorted(p.relative_to(refs_dir).as_posix() for p in refs_dir.rglob("*.md"))
        if scripts_dir.exists():
            scripts_list = sorted(p.relative_to(scripts_dir).as_posix() for p in scripts_dir.rglob("*.py"))

        manifest = {
            "references": refs_list,
            "scripts": scripts_list,
        }

        return (
            f"<skill name=\"{name}\">\n"
            f"{skill['body']}\n"
            f"</skill>\n"
            f"<skill_manifest name=\"{name}\">\n"
            f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n"
            f"</skill_manifest>"
        )

    def _resolve_skill_dir(self, name: str) -> Path | None:
        """根据技能名解析技能目录路径。"""
        skill = self.skills.get(name)
        if not skill:
            return None
        return Path(skill["path"]).parent

    def get_references_content(self, name: str, doc_path: str = "") -> str:
        """读取 references 文档；未指定 doc_path 时返回可用文档列表。"""
        skill_dir = self._resolve_skill_dir(name)
        if not skill_dir:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"

        refs_dir = skill_dir / "references"
        if not refs_dir.exists():
            return f"Error: Skill '{name}' has no references directory"

        if not doc_path:
            files = sorted(p.relative_to(refs_dir).as_posix() for p in refs_dir.rglob("*.md"))
            return json.dumps({"skill": name, "references": files}, ensure_ascii=False, indent=2)

        target = (refs_dir / doc_path).resolve()
        if not target.is_relative_to(refs_dir):
            return "Error: references path escapes skill directory"
        if not target.exists() or not target.is_file():
            return f"Error: Reference doc not found: {doc_path}"

        content = read_text_safe(target)
        return (
            f"### Skill Reference\n"
            f"- skill: `{name}`\n"
            f"- path: `{doc_path}`\n\n"
            f"```markdown\n{content}\n```"
        )

    def get_scripts_content(self, name: str, script_path: str = "") -> str:
        """读取 scripts 脚本；未指定 script_path 时返回可用脚本列表。"""
        skill_dir = self._resolve_skill_dir(name)
        if not skill_dir:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"

        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            return f"Error: Skill '{name}' has no scripts directory"

        if not script_path:
            files = sorted(p.relative_to(scripts_dir).as_posix() for p in scripts_dir.rglob("*.py"))
            return json.dumps({"skill": name, "scripts": files}, ensure_ascii=False, indent=2)

        target = (scripts_dir / script_path).resolve()
        if not target.is_relative_to(scripts_dir):
            return "Error: scripts path escapes skill directory"
        if not target.exists() or not target.is_file():
            return f"Error: Script not found: {script_path}"

        content = read_text_safe(target)
        return (
            f"### Skill Script\n"
            f"- skill: `{name}`\n"
            f"- path: `{script_path}`\n\n"
            f"```python\n{content}\n```"
        )

    def _backup_skill(self, name: str, reason: str = "") -> Path:
        """备份 skill 文件到 .backups/skills/YYYY-MM-DD/skill-name/"""
        skill = self.skills.get(name)
        if not skill:
            raise ValueError(f"Unknown skill: {name}")

        skill_path = Path(skill["path"])
        today = datetime.now().strftime("%Y-%m-%d")
        timestamp = datetime.now().strftime("%H-%M-%S")

        backup_dir = self.backups_dir / today / name
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path = backup_dir / f"SKILL-{timestamp}.md"

        # 读取并添加元数据
        content = read_text_safe(skill_path)
        metadata = f"<!-- Backup: {timestamp} | Reason: {reason} -->\n"
        backup_path.write_text(metadata + content, encoding="utf-8")

        return backup_path

    def update_skill(self, name: str, old_text: str = None, new_text: str = None,
                     full_content: str = None, reason: str = "") -> str:
        """更新 skill 文件，自动备份。

        Args:
            name: skill 名称
            old_text: 要替换的旧文本（增量模式）
            new_text: 新文本（增量模式）
            full_content: 完整新内容（替换模式）
            reason: 修改原因，用于备份记录

        Returns:
            操作结果描述
        """
        skill = self.skills.get(name)
        if not skill:
            return f"Error: Unknown skill '{name}'. Available: {', '.join(self.skills.keys())}"

        skill_path = Path(skill["path"])

        try:
            # 1. 备份
            backup_path = self._backup_skill(name, reason)

            # 2. 执行修改
            if full_content:
                # 完整替换模式
                # 保留 frontmatter
                _, body = self._parse_frontmatter(full_content)
                meta = skill["meta"]
                frontmatter_lines = ["---"]
                for key, val in meta.items():
                    frontmatter_lines.append(f"{key}: {val}")
                frontmatter_lines.append("---")
                new_content = "\n".join(frontmatter_lines) + "\n\n" + body
                skill_path.write_text(new_content, encoding="utf-8")

            elif old_text and new_text:
                # 增量编辑模式
                content = read_text_safe(skill_path)
                if old_text not in content:
                    return f"Error: old_text not found in skill '{name}'. No changes made."
                new_content = content.replace(old_text, new_text, 1)
                skill_path.write_text(new_content, encoding="utf-8")

            else:
                return "Error: Must provide either (full_content) or (old_text + new_text)"

            # 3. 重载 skill
            self._reload_skill(name)

            return f"Updated skill '{name}'. Backup: {backup_path}"

        except Exception as e:
            return f"Error updating skill '{name}': {e}"

    def _reload_skill(self, name: str):
        """重新加载单个 skill。"""
        skill = self.skills.get(name)
        if not skill:
            return
        path = Path(skill["path"])
        text = read_text_safe(path)
        meta, body = self._parse_frontmatter(text)
        self.skills[name] = {"meta": meta, "body": body, "path": str(path)}


SKILL_LOADER = SkillLoader(SKILLS_DIR)

# 第 1 层：将技能元数据注入 system prompt
SYSTEM = f"""You are a helpful assistant at {WORKDIR}.

INSTRUCTIONS:
1. Read the skill descriptions below
2. Call load_skill() with the skill that matches the user's question
3. Follow the loaded skill's instructions to answer
4. Runtime OS is Windows only. Shell commands must be Windows PowerShell compatible.

SKILLS:
{SKILL_LOADER.get_descriptions()}

IMPORTANT: Always call load_skill() before answering. The skill contains the specialized knowledge needed."""

@tool(name="load_skill", description="Load specialized knowledge by name.")
def load_skill(name: str) -> str:
    return SKILL_LOADER.get_content(name)


@tool(name="load_skill_reference", description="Load one reference document from a skill; omit path to list available docs.")
def load_skill_reference(name: str, path: str = "") -> str:
    return SKILL_LOADER.get_references_content(name, path)


@tool(name="load_skill_script", description="Load one script from a skill; omit path to list available scripts.")
def load_skill_script(name: str, path: str = "") -> str:
    return SKILL_LOADER.get_scripts_content(name, path)


@tool(name="update_skill", description="Update a skill file. Use old_text+new_text for incremental edits, or full_content for complete replacement.")
def update_skill(name: str, old_text: str = "", new_text: str = "",
                 full_content: str = "", reason: str = "") -> str:
    """
    更新 skill 文件。

    参数:
        name: skill 名称
        old_text: 要替换的旧文本（增量编辑模式）
        new_text: 新文本（增量编辑模式）
        full_content: 完整新内容（完整替换模式）
        reason: 修改原因（用于备份记录）
    """
    return SKILL_LOADER.update_skill(
        name,
        old_text or None,
        new_text or None,
        full_content or None,
        reason
    )


# 技能加载工具放前面，让模型优先看到
TOOLS =  OPS.get_tools()+[load_skill, load_skill_reference, load_skill_script, update_skill]


def _serialize_content_block(block):
    """将自定义内容块转换为可 JSON 序列化结构，便于日志落盘。"""
    if isinstance(block, dict):
        return block

    block_type = getattr(block, "type", None)
    if block_type == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if block_type == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": getattr(block, "input", {}),
        }

    # 未知对象类型的兜底处理。
    return str(block)


def _serialize_messages_for_log(messages: list) -> list:
    safe_messages = []
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, list):
            safe_content = [_serialize_content_block(item) for item in content]
        else:
            safe_content = content
        safe_messages.append({"role": role, "content": safe_content})
    return safe_messages


def _write_latest_log(messages: list):
    """覆盖旧日志，仅保留最新的完整会话快照。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_serialize_messages_for_log(messages), ensure_ascii=False)
    # 同步覆盖写，避免异步日志竞争。
    LOG_FILE.write_text(payload + "\n", encoding="utf-8")


def _on_stop(messages: list, response):
    """在模型结束本轮对话时写入最新日志快照。"""
    _write_latest_log(messages)


_S05_STREAM_STATE = {"printed": False}


def _on_stream_token(token: str, block, messages: list, response):
    """按 token 粒度流式打印模型输出。"""
    _ = block
    _ = messages
    _ = response
    logger.opt(raw=True).info(token)
    _S05_STREAM_STATE["printed"] = True


AGENT_LOOP = BaseAgentLoop(
    provider=provider,
    model=MODEL,
    system=SYSTEM,
    tools=TOOLS,
    max_tokens=8000,
    max_rounds=10,  # 限制最多10轮对话
)


def agent_loop(messages: list):
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36ms05 >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        _S05_STREAM_STATE["printed"] = False
        agent_loop(history)
        if not _S05_STREAM_STATE["printed"]:
            response_content = history[-1]["content"]
            if isinstance(response_content, list):
                for block in response_content:
                    if hasattr(block, "text"):
                        logger.info(block.text)
        logger.info("")
