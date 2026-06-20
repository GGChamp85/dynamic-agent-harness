"""Base Agent with governance hooks and knowledge graph access."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import structlog
from harness.knowledge_graph import KnowledgeGraph

logger = structlog.get_logger()

@dataclass
class ActionResult:
    agent: str
    action: str
    status: str
    output: Any = None
    approved_by: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

class Agent:
    """Supervised AI agent with built-in governance."""
    def __init__(self, name: str, role: str, skills: list[str] | None = None,
                 knowledge_graph: KnowledgeGraph | None = None,
                 model: str = "claude-sonnet-4-6", max_actions_per_turn: int = 10):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.role = role
        self.skills = skills or []
        self.knowledge_graph = knowledge_graph
        self.model = model
        self.max_actions_per_turn = max_actions_per_turn
        self._action_count = 0
        self._audit_log: list[ActionResult] = []

    def can_handle(self, task: str) -> float:
        task_lower = task.lower()
        matches = sum(1 for s in self.skills if s.lower() in task_lower)
        return min(1.0, matches / max(len(self.skills), 1) + 0.1)

    def plan(self, task: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        kg_context = {}
        if self.knowledge_graph and context:
            for eid in context.get("entities", []):
                kg_context[eid] = self.knowledge_graph.query(eid)
        return [
            {"step": 1, "action": f"analyze-{task[:30]}", "description": f"Analyze using {self.role}", "requires_approval": False, "kg_context": kg_context},
            {"step": 2, "action": f"execute-{task[:30]}", "description": "Execute planned changes", "requires_approval": True},
            {"step": 3, "action": "validate", "description": "Validate results", "requires_approval": False},
        ]

    def execute(self, task: str, context: dict[str, Any] | None = None, approval_callback: Any = None) -> list[ActionResult]:
        plan = self.plan(task, context)
        results: list[ActionResult] = []
        for step in plan:
            if self._action_count >= self.max_actions_per_turn:
                break
            if step.get("requires_approval") and approval_callback:
                approved, approver = approval_callback(self.name, step)
                if not approved:
                    r = ActionResult(agent=self.name, action=step["action"], status="denied")
                    results.append(r); self._audit_log.append(r)
                    break
                r = ActionResult(agent=self.name, action=step["action"], status="approved", approved_by=approver, output=f"Executed: {step['description']}")
            else:
                r = ActionResult(agent=self.name, action=step["action"], status="executed", output=f"Executed: {step['description']}")
            results.append(r); self._audit_log.append(r); self._action_count += 1
            logger.info("action_completed", agent=self.name, action=step["action"], status=r.status)
        return results

    @property
    def audit_log(self) -> list[ActionResult]:
        return list(self._audit_log)

    def reset_turn(self) -> None:
        self._action_count = 0

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, role={self.role!r}, skills={self.skills})"
