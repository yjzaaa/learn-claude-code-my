"""Message serialization and JSONL logging helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def _serialize_content_block(block: Any) -> Any:
    """Convert message content blocks into JSON-serializable structures."""
    if isinstance(block, (str, int, float, bool)) or block is None:
        return block

    if isinstance(block, dict):
        return {k: _serialize_content_block(v) for k, v in block.items()}

    if isinstance(block, list):
        return [_serialize_content_block(item) for item in block]

    block_type = getattr(block, "type", None)
    if block_type == "text":
        return {"type": "text", "text": getattr(block, "text", "")}
    if block_type == "tool_use":
        return {
            "type": "tool_use",
            "id": getattr(block, "id", ""),
            "name": getattr(block, "name", ""),
            "input": _serialize_content_block(getattr(block, "input", {})),
        }

    return str(block)


def _serialize_messages_for_log(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Serialize complete message history while preserving role/content shape."""
    serialized: List[Dict[str, Any]] = []
    for msg in messages:
        serialized.append(
            {
                "role": msg.get("role"),
                "content": _serialize_content_block(msg.get("content")),
            }
        )
    return serialized


def append_messages_jsonl(
    messages: List[Dict[str, Any]],
    log_dir: Path,
    log_file: Path,
) -> None:
    """Write only the latest full message snapshot as a single JSONL line."""
    log_dir.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(_serialize_messages_for_log(messages), ensure_ascii=False)
    # Overwrite old snapshots so the file always reflects the latest full state.
    with log_file.open("w", encoding="utf-8") as f:
        f.write(payload + "\n")
