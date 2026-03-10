"""API integration tests for skill edit HITL endpoints."""

from __future__ import annotations

import unittest
import uuid

from fastapi.testclient import TestClient

from agents.api.main_new import create_app
from agents.session.skill_edit_hitl import skill_edit_hitl_store


class SkillEditHITLApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.client = TestClient(self.app)
        self.dialog_id = f"dlg_{uuid.uuid4().hex}"

    def test_pending_and_reject_decision_flow(self) -> None:
        proposal = skill_edit_hitl_store.create_proposal(
            dialog_id=self.dialog_id,
            path="skills/finance/SKILL.md",
            old_content="old",
            new_content="new",
            reason="api-test",
        )

        pending_resp = self.client.get(
            f"/api/skill-edits/pending?dialog_id={self.dialog_id}",
        )
        self.assertEqual(pending_resp.status_code, 200)
        pending_payload = pending_resp.json()
        self.assertTrue(pending_payload["success"])
        self.assertEqual(len(pending_payload["data"]), 1)
        self.assertEqual(pending_payload["data"][0]["approval_id"], proposal.approval_id)

        decision_resp = self.client.post(
            f"/api/skill-edits/{proposal.approval_id}/decision",
            json={"decision": "reject"},
        )
        self.assertEqual(decision_resp.status_code, 200)
        decision_payload = decision_resp.json()
        self.assertTrue(decision_payload["success"])
        self.assertEqual(decision_payload["data"]["status"], "rejected")

        pending_after = self.client.get(
            f"/api/skill-edits/pending?dialog_id={self.dialog_id}",
        )
        self.assertEqual(pending_after.status_code, 200)
        pending_after_payload = pending_after.json()
        self.assertEqual(pending_after_payload["data"], [])


if __name__ == "__main__":
    unittest.main()
