#!/usr/bin/env python3
"""s02 + skill_loader agent.

This agent keeps the default tool-calling workflow from s02 and adds
an on-demand skill loader tool inspired by s05.
"""

import os
import re
import json
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger

try:
    from agents.providers import create_provider_from_env
    from agents.base import BaseAgentLoop, WorkspaceOps, tool, build_tools_and_handlers
except ImportError:
    from providers import create_provider_from_env
    from base import BaseAgentLoop, WorkspaceOps, tool, build_tools_and_handlers


WORKDIR = Path.cwd()
SKILLS_DIR = WORKDIR / "skills"

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)


class SkillLoader:
    """Load skill metadata and full body from skills/*/SKILL.md."""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, dict[str, str]] = {}
        self._load_all()

    def _load_all(self) -> None:
        self.skills = {}
        if not self.skills_dir.exists():
            return
        for f in sorted(self.skills_dir.rglob("SKILL.md")):
            text = self._read_text_safe(f)
            meta, body = self._parse_frontmatter(text)
            name = meta.get("name", f.parent.name)
            self.skills[name] = {
                "description": meta.get("description", "No description"),
                "body": body,
                "path": str(f),
            }

    @staticmethod
    def _read_text_safe(path: Path) -> str:
        for enc in ("utf-8", "utf-8-sig", "gbk"):
            try:
                return path.read_text(encoding=enc)
            except UnicodeDecodeError:
                continue
        return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        meta: dict[str, str] = {}
        for line in match.group(1).strip().splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
        return meta, match.group(2).strip()

    def get_descriptions(self) -> str:
        if not self.skills:
            return "(no skills available)"
        lines = []
        for name, skill in self.skills.items():
            lines.append(f"  - {name}: {skill['description']}")
        return "\n".join(lines)

    def get_content(self, name: str) -> str:
        skill = self.skills.get(name)
        if not skill:
            available = ", ".join(sorted(self.skills.keys())) or "(none)"
            return f"Error: Unknown skill '{name}'. Available: {available}"

        skill_dir = Path(skill["path"]).parent
        refs_dir = skill_dir / "references"
        scripts_dir = skill_dir / "scripts"

        refs = sorted(p.relative_to(refs_dir).as_posix() for p in refs_dir.rglob("*.md")) if refs_dir.exists() else []
        scripts = sorted(p.relative_to(scripts_dir).as_posix() for p in scripts_dir.rglob("*.py")) if scripts_dir.exists() else []

        manifest = {"references": refs, "scripts": scripts}

        return (
            f"<skill name=\"{name}\">\n{skill['body']}\n</skill>\n"
            f"<skill_manifest name=\"{name}\">\n"
            f"{json.dumps(manifest, ensure_ascii=False, indent=2)}\n"
            f"</skill_manifest>"
        )

    def _resolve_skill_dir(self, name: str) -> Path | None:
        skill = self.skills.get(name)
        if not skill:
            return None
        return Path(skill["path"]).parent

    def get_references_content(self, name: str, doc_path: str = "") -> str:
        """Load one references doc progressively, or list docs when path is empty."""
        skill_dir = self._resolve_skill_dir(name)
        if not skill_dir:
            available = ", ".join(sorted(self.skills.keys())) or "(none)"
            return f"Error: Unknown skill '{name}'. Available: {available}"

        refs_dir = skill_dir / "references"
        if not refs_dir.exists():
            return f"Error: Skill '{name}' has no references directory"

        if not doc_path:
            files = sorted(p.relative_to(refs_dir).as_posix() for p in refs_dir.rglob("*.md"))
            return json.dumps({"skill": name, "references": files}, ensure_ascii=False, indent=2)

        target = (refs_dir / doc_path).resolve()
        if not target.is_relative_to(refs_dir.resolve()):
            return "Error: references path escapes skill directory"
        if not target.exists() or not target.is_file():
            return f"Error: Reference doc not found: {doc_path}"

        content = self._read_text_safe(target)
        return (
            f"### Skill Reference\n"
            f"- skill: `{name}`\n"
            f"- path: `{doc_path}`\n\n"
            f"```markdown\n{content}\n```"
        )

    def get_scripts_content(self, name: str, script_path: str = "") -> str:
        """Load one scripts file progressively, or list scripts when path is empty."""
        skill_dir = self._resolve_skill_dir(name)
        if not skill_dir:
            available = ", ".join(sorted(self.skills.keys())) or "(none)"
            return f"Error: Unknown skill '{name}'. Available: {available}"

        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            return f"Error: Skill '{name}' has no scripts directory"

        if not script_path:
            files = sorted(p.relative_to(scripts_dir).as_posix() for p in scripts_dir.rglob("*.py"))
            return json.dumps({"skill": name, "scripts": files}, ensure_ascii=False, indent=2)

        normalized = str(script_path).strip().replace("\\", "/")
        normalized = re.sub(r"^\./", "", normalized)
        if normalized.lower().startswith("scripts/"):
            normalized = normalized[len("scripts/"):]

        # 兼容省略 .py 的调用。
        candidates = [normalized]
        if normalized and not normalized.lower().endswith(".py"):
            candidates.append(f"{normalized}.py")

        target = None
        used_path = normalized
        scripts_root = scripts_dir.resolve()
        for candidate in candidates:
            if not candidate:
                continue
            candidate_target = (scripts_dir / candidate).resolve()
            if not candidate_target.is_relative_to(scripts_root):
                continue
            if candidate_target.exists() and candidate_target.is_file():
                target = candidate_target
                used_path = candidate
                break

        if target is None:
            return f"Error: Script not found: {script_path}"

        content = self._read_text_safe(target)
        return (
            f"### Skill Script\n"
            f"- skill: `{name}`\n"
            f"- path: `{used_path}`\n\n"
            f"```python\n{content}\n```"
        )


SKILL_LOADER = SkillLoader(SKILLS_DIR)
provider = create_provider_from_env()
MODEL = provider.default_model if provider else "deepseek-chat"
OPS = WorkspaceOps(workdir=WORKDIR)

SYSTEM = f"""You are a coding agent at {WORKDIR}. Use tools to solve tasks.

Runtime OS is Windows.
Skills available:
{SKILL_LOADER.get_descriptions()}

Skill usage policy:
1. If the user explicitly asks to use a skill (for example: "use finance skill", "使用finance技能"), you MUST call load_skill(name) before answering.
2. After load_skill(name), read the returned manifest and only load extra references/scripts when required.
3. Do not claim a skill is unavailable unless load_skill returns an explicit error.
4. Never output pseudo tool-call JSON in plain text (for example: {{"command":"..."}}). If execution is needed, invoke the real tool/function call instead.

Progressive loading rule:
1. Call load_skill(name) first to get overview + manifest.
2. Call load_skill_reference(name, path) for specific docs.
3. Call load_skill_script(name, path) for executable script details.
Only load extra files when needed.
"""


@tool(name="load_skill", description="Load full skill content by skill name.")
def load_skill(name: str) -> str:
    return SKILL_LOADER.get_content(name)


@tool(name="load_skill_reference", description="Load a references document from a skill; omit path to list docs.")
def load_skill_reference(name: str, path: str = "") -> str:
    return SKILL_LOADER.get_references_content(name, path)


@tool(name="load_skill_script", description="Load a scripts file from a skill; omit path to list scripts.")
def load_skill_script(name: str, path: str = "") -> str:
    return SKILL_LOADER.get_scripts_content(name, path)


class S02WithSkillLoaderAgent(BaseAgentLoop):
    """s02-style tool-use agent with s05-style skill loading."""

    def __init__(self, *, max_tokens: int = 8000, max_rounds: int = 25, **kwargs) -> None:
        base_tools = OPS.get_tools()
        if isinstance(base_tools, dict):
            tool_functions = list(base_tools.values()) + [load_skill, load_skill_reference, load_skill_script]
        else:
            tool_functions = base_tools + [load_skill, load_skill_reference, load_skill_script]

        tools, tool_handlers = build_tools_and_handlers(tool_functions)

        super().__init__(
            provider=provider,
            model=MODEL,
            system=SYSTEM,
            tools=tools,
            tool_handlers=tool_handlers,
            max_tokens=max_tokens,
            max_rounds=max_rounds,
            **kwargs,
        )


AGENT_LOOP = S02WithSkillLoaderAgent()


def agent_loop(messages: list) -> None:
    AGENT_LOOP.run(messages)


if __name__ == "__main__":
    history = []
    while True:
        try:
            query = input("\033[36magent >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit", ""):
            break
        history.append({"role": "user", "content": query})
        agent_loop(history)
        response_content = history[-1]["content"]
        if isinstance(response_content, list):
            for block in response_content:
                if hasattr(block, "text"):
                    logger.info(block.text)
        logger.info("")
