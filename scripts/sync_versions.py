#!/usr/bin/env python3
"""
Sync package versions from virtual environment to pyproject.toml

Usage:
    python scripts/sync_versions.py
"""

import subprocess
import re
from pathlib import Path


def get_installed_versions():
    """Get all installed package versions from pip"""
    result = subprocess.run(
        ["pip", "list", "--format=freeze"],
        capture_output=True,
        text=True
    )
    versions = {}
    for line in result.stdout.strip().split("\n"):
        if "==" in line:
            name, version = line.split("==", 1)
            versions[name.lower()] = version
    return versions


def update_pyproject_versions(pyproject_path: Path, installed_versions: dict):
    """Update versions in pyproject.toml dependencies"""
    content = pyproject_path.read_text(encoding="utf-8")

    # Pattern to match dependency lines like: "package>=1.0" or "package==1.0"
    dep_pattern = re.compile(
        r'^([\s]*)"([a-zA-Z0-9_-]+)([<>=!~^]+)([^"]*)"([\s,]*)$',
        re.MULTILINE
    )

    def replace_version(match):
        indent = match.group(1)
        pkg_name = match.group(2)
        operator = match.group(3)
        suffix = match.group(5)

        # Skip if no version constraint or if it's a range
        if operator in (">=", "<=", ">", "<", "~="):
            return match.group(0)

        # Look for installed version
        installed_version = installed_versions.get(pkg_name.lower())
        if installed_version:
            return f'{indent}"{pkg_name}=={installed_version}"{suffix}'

        return match.group(0)

    updated_content = dep_pattern.sub(replace_version, content)

    # Write back
    pyproject_path.write_text(updated_content, encoding="utf-8")
    print(f"✅ Updated {pyproject_path}")


def main():
    print("🔍 Scanning virtual environment packages...")
    installed = get_installed_versions()
    print(f"Found {len(installed)} packages")

    pyproject = Path("pyproject.toml")
    if not pyproject.exists():
        print("❌ pyproject.toml not found")
        return 1

    print("📝 Updating pyproject.toml...")
    update_pyproject_versions(pyproject, installed)

    print("\n📋 Key packages synced:")
    key_packages = [
        "anthropic", "fastapi", "uvicorn", "pydantic", "python-dotenv",
        "httpx", "loguru", "langchain", "litellm", "langgraph",
        "deepagents", "websockets", "langchain-litellm"
    ]
    for pkg in key_packages:
        if pkg in installed:
            print(f"  • {pkg}=={installed[pkg]}")

    return 0


if __name__ == "__main__":
    exit(main())
