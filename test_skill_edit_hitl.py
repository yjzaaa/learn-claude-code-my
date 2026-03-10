"""Tests for skill edit HITL approval flow."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agents.session.skill_edit_hitl import SkillEditHITLStore


class SkillEditHITLStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.workdir = Path(self.tmpdir.name)
        self.skill_file = self.workdir / "skills" / "demo" / "SKILL.md"
        self.skill_file.parent.mkdir(parents=True, exist_ok=True)
        self.skill_file.write_text("old-content\n", encoding="utf-8")
        self.store = SkillEditHITLStore(self.workdir)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_and_list_pending(self) -> None:
        proposal = self.store.create_proposal(
            dialog_id="d1",
            path="skills/demo/SKILL.md",
            old_content="old-content\n",
            new_content="new-content\n",
            reason="test",
        )

        pending = self.store.list_pending(dialog_id="d1")
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["approval_id"], proposal.approval_id)
        self.assertEqual(pending[0]["status"], "pending")
        self.assertIn("@@", pending[0]["unified_diff"])

    def test_decide_reject_keeps_file(self) -> None:
        proposal = self.store.create_proposal(
            dialog_id="d1",
            path="skills/demo/SKILL.md",
            old_content="old-content\n",
            new_content="new-content\n",
            reason="test",
        )

        result = self.store.decide(proposal.approval_id, "reject")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "rejected")
        self.assertEqual(self.skill_file.read_text(encoding="utf-8"), "old-content\n")

    def test_decide_accept_writes_file(self) -> None:
        proposal = self.store.create_proposal(
            dialog_id="d1",
            path="skills/demo/SKILL.md",
            old_content="old-content\n",
            new_content="accepted-content\n",
            reason="test",
        )

        result = self.store.decide(proposal.approval_id, "accept")
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "accepted")
        self.assertEqual(self.skill_file.read_text(encoding="utf-8"), "accepted-content\n")

    def test_decide_edit_accept_writes_edited_content(self) -> None:
        proposal = self.store.create_proposal(
            dialog_id="d1",
            path="skills/demo/SKILL.md",
            old_content="old-content\n",
            new_content="new-content\n",
            reason="test",
        )

        result = self.store.decide(
            proposal.approval_id,
            "edit_accept",
            edited_content="edited-content\n",
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["data"]["status"], "edited_accepted")
        self.assertEqual(self.skill_file.read_text(encoding="utf-8"), "edited-content\n")
        self.assertIn("edited-content", result["data"]["new_content"])

    def test_decide_rejects_outside_skills_path(self) -> None:
        proposal = self.store.create_proposal(
            dialog_id="d1",
            path="README.md",
            old_content="old",
            new_content="new",
            reason="test",
        )

        result = self.store.decide(proposal.approval_id, "accept")
        self.assertFalse(result["success"])
        self.assertEqual(result["message"], "path is outside skills")


if __name__ == "__main__":
    unittest.main()
