"""
Skill ID Sidecar - 技能 ID 持久化管理

管理 .skill_id 文件的读取、创建和写入，支持技能版本演化。
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import TYPE_CHECKING

from backend.domain.models.agent.skill_engine_types import SkillMeta, SkillOrigin
from backend.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

SIDECAR_FILENAME = ".skill_id"


def _generate_uuid8() -> str:
    """生成 8 字符 UUID（UUID4 的前 8 位）"""
    return uuid.uuid4().hex[:8]


def _generate_skill_id(name: str, origin: SkillOrigin = SkillOrigin.IMPORTED, generation: int = 1) -> str:
    """生成技能 ID

    Args:
        name: 技能名称
        origin: 技能来源类型
        generation: 进化代数

    Returns:
        格式化的技能 ID
    """
    uuid_suffix = _generate_uuid8()

    if origin == SkillOrigin.IMPORTED:
        return f"{name}__imp_{uuid_suffix}"
    else:
        # 进化技能: name__v{gen}_{uuid8}
        return f"{name}__v{generation}_{uuid_suffix}"


def _read_or_create_skill_id(
    skill_dir: Path,
    name: str,
    origin: SkillOrigin = SkillOrigin.IMPORTED,
    generation: int = 1,
) -> tuple[str, bool]:
    """读取或创建技能 ID

    优先读取已存在的 .skill_id 文件，如果不存在则生成新 ID 并尝试写入。

    Args:
        skill_dir: 技能目录路径
        name: 技能名称
        origin: 技能来源类型
        generation: 进化代数

    Returns:
        (skill_id, is_new) 元组
    """
    sidecar_path = skill_dir / SIDECAR_FILENAME

    # 尝试读取已存在的 sidecar
    if sidecar_path.exists():
        try:
            content = sidecar_path.read_text(encoding="utf-8").strip()

            # 验证格式：应该包含 name 和 uuid 部分
            if content and "__" in content:
                # 基本验证：检查是否符合 {name}__{type}_{uuid8} 格式
                parts = content.split("__")
                if len(parts) == 2:
                    suffix_part = parts[1]
                    if "_" in suffix_part and len(suffix_part.split("_")[-1]) == 8:
                        logger.debug(f"[SkillIDSidecar] Read existing ID from {sidecar_path}: {content}")
                        return content, False

            # 格式无效，记录警告并继续生成新 ID
            logger.warning(f"[SkillIDSidecar] Invalid format in {sidecar_path}, regenerating ID")

        except PermissionError:
            logger.warning(f"[SkillIDSidecar] Permission denied reading {sidecar_path}, generating in-memory ID")
        except UnicodeDecodeError:
            logger.warning(f"[SkillIDSidecar] Corrupted file {sidecar_path}, regenerating ID")
        except Exception as e:
            logger.warning(f"[SkillIDSidecar] Error reading {sidecar_path}: {e}, generating in-memory ID")

    # 生成新 ID
    skill_id = _generate_skill_id(name, origin, generation)

    # 尝试写入 sidecar
    try:
        sidecar_path.write_text(skill_id + "\n", encoding="utf-8")
        logger.info(f"[SkillIDSidecar] Created new ID at {sidecar_path}: {skill_id}")
    except PermissionError:
        logger.warning(f"[SkillIDSidecar] Permission denied writing {sidecar_path}, using in-memory ID only")
    except IsADirectoryError:
        logger.error(f"[SkillIDSidecar] Cannot write {sidecar_path}: is a directory")
    except Exception as e:
        logger.warning(f"[SkillIDSidecar] Error writing {sidecar_path}: {e}, using in-memory ID only")

    return skill_id, True


def read_skill_id(skill_dir: Path) -> str | None:
    """读取技能 ID（仅读取，不创建）

    Args:
        skill_dir: 技能目录路径

    Returns:
        技能 ID 或 None（如果文件不存在）
    """
    sidecar_path = skill_dir / SIDECAR_FILENAME

    if not sidecar_path.exists():
        return None

    try:
        content = sidecar_path.read_text(encoding="utf-8").strip()
        if content and "__" in content:
            return content
        return None
    except Exception:
        return None


def write_skill_id(skill_dir: Path, skill_id: str) -> bool:
    """写入技能 ID

    Args:
        skill_dir: 技能目录路径
        skill_id: 技能 ID

    Returns:
        是否成功写入
    """
    sidecar_path = skill_dir / SIDECAR_FILENAME

    try:
        sidecar_path.write_text(skill_id + "\n", encoding="utf-8")
        logger.debug(f"[SkillIDSidecar] Wrote ID to {sidecar_path}: {skill_id}")
        return True
    except PermissionError:
        logger.warning(f"[SkillIDSidecar] Permission denied writing {sidecar_path}")
        return False
    except Exception as e:
        logger.warning(f"[SkillIDSidecar] Error writing {sidecar_path}: {e}")
        return False


def generate_evolved_skill_id(parent_meta: SkillMeta, new_generation: int | None = None) -> str:
    """为进化技能生成新 ID

    Args:
        parent_meta: 父技能元数据
        new_generation: 指定新代数（默认 parent + 1）

    Returns:
        新的技能 ID
    """
    generation = new_generation or (parent_meta.generation + 1)
    return _generate_skill_id(
        name=parent_meta.name,
        origin=SkillOrigin.EVOLVED,
        generation=generation,
    )


def parse_skill_id(skill_id: str) -> tuple[str, str, int] | None:
    """解析技能 ID

    Args:
        skill_id: 技能 ID

    Returns:
        (name, origin_type, generation) 或 None（如果格式无效）
    """
    try:
        if "__imp_" in skill_id:
            name = skill_id.split("__imp_")[0]
            return name, "imported", 1
        elif "__v" in skill_id:
            name_part = skill_id.split("__v")[0]
            version_part = skill_id.split("__v")[1]
            generation = int(version_part.split("_")[0])
            return name_part, "evolved", generation
        return None
    except Exception:
        return None
