"""Plan Plugin - Plan approval gate for agents."""

from __future__ import annotations

import time
from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable

from ..base import tool
from .base import AgentPlugin

if TYPE_CHECKING:
    from ..agent.base_agent_loop import BaseAgentLoop


class PlanGate:
    """Plan approval gate."""

    def __init__(self):
        self.pending_plans: dict[str, dict] = {}

    def submit(self, plan: str) -> str:
        """Submit a plan for approval."""
        plan_id = f"plan_{int(time.time() * 1000)}"
        self.pending_plans[plan_id] = {
            "id": plan_id,
            "plan": plan,
            "status": "pending",
            "submitted_at": datetime.now().isoformat(),
        }
        return plan_id

    def review(self, plan_id: str, approve: bool, feedback: str = "") -> dict | None:
        """Review a plan."""
        plan = self.pending_plans.get(plan_id)
        if not plan:
            return None
        plan["status"] = "approved" if approve else "rejected"
        plan["feedback"] = feedback
        plan["reviewed_at"] = datetime.now().isoformat()
        return plan

    def get(self, plan_id: str) -> dict | None:
        """Get plan by ID."""
        return self.pending_plans.get(plan_id)

    def is_approved(self, plan_id: str) -> bool:
        """Check if plan is approved."""
        plan = self.pending_plans.get(plan_id)
        return plan is not None and plan.get("status") == "approved"


class PlanPlugin(AgentPlugin):
    """Plugin providing plan approval gate functionality.

    Allows agents to submit plans for approval before execution.
    Supports plan review (approve/reject with feedback).
    """

    def __init__(self):
        super().__init__()
        self._gate = PlanGate()

    @property
    def name(self) -> str:
        return "plan"

    def get_tools(self) -> list[Callable]:
        return [
            self._submit_plan,
            self._review_plan,
            self._get_plan,
        ]

    @tool(
        name="submit_plan",
        description="Submit a plan for approval. Returns plan_id."
    )
    def _submit_plan(self, plan: str) -> str:
        """Submit a plan for approval.

        Args:
            plan: The plan text to submit.

        Returns:
            JSON with plan_id and status.
        """
        import json as json_mod
        plan_id = self._gate.submit(plan)
        return json_mod.dumps({
            "plan_id": plan_id,
            "status": "pending"
        })

    @tool(
        name="review_plan",
        description="Review a plan. approve=True to approve, False to reject."
    )
    def _review_plan(self, plan_id: str, approve: bool, feedback: str = "") -> str:
        """Review a plan.

        Args:
            plan_id: The plan ID to review.
            approve: True to approve, False to reject.
            feedback: Optional feedback message.

        Returns:
            JSON with updated plan status.
        """
        import json as json_mod
        plan = self._gate.review(plan_id, approve, feedback)
        if plan:
            return json_mod.dumps(plan, ensure_ascii=False)
        return json_mod.dumps({"error": f"Plan {plan_id} not found"})

    @tool(
        name="get_plan",
        description="Get plan status by ID."
    )
    def _get_plan(self, plan_id: str) -> str:
        """Get plan by ID.

        Args:
            plan_id: The plan ID to retrieve.

        Returns:
            JSON with plan details.
        """
        import json as json_mod
        plan = self._gate.get(plan_id)
        if plan:
            return json_mod.dumps(plan, ensure_ascii=False)
        return json_mod.dumps({"error": f"Plan {plan_id} not found"})

    def is_approved(self, plan_id: str) -> bool:
        """Check if a plan is approved."""
        return self._gate.is_approved(plan_id)
