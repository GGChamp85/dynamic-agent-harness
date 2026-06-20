"""Multi-agent orchestrator with governance checkpoints."""
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import structlog
from harness.agent import Agent, ActionResult
from harness.governance import ApprovalGate, AuditTrail
from harness.memory import MemoryPipeline

logger = structlog.get_logger()

@dataclass
class ExecutionResult:
    task: str
    status: str
    agents_used: list[str]
    actions: list[ActionResult] = field(default_factory=list)
    cost_usd: float = 0.0
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None

    @property
    def summary(self) -> str:
        executed = sum(1 for a in self.actions if a.status in ("executed", "approved"))
        denied = sum(1 for a in self.actions if a.status == "denied")
        return f"Run {self.run_id}: {self.status} | {len(self.agents_used)} agents, {len(self.actions)} actions (ok={executed}, denied={denied}) | ${self.cost_usd:.2f}"

    @property
    def audit_log(self) -> list[dict[str, Any]]:
        return [{"agent": a.agent, "action": a.action, "status": a.status, "approved_by": a.approved_by, "timestamp": a.timestamp, "trace_id": a.trace_id} for a in self.actions]

    @property
    def cost_breakdown(self) -> dict[str, float]:
        costs: dict[str, float] = {}
        for a in self.actions:
            costs[a.agent] = costs.get(a.agent, 0) + 0.05
        return costs

class Orchestrator:
    """Routes tasks to agents, manages execution, enforces governance."""
    COST_PER_ACTION = 0.05
    def __init__(self, agents: list[Agent], approval_gate: ApprovalGate | None = None, memory: MemoryPipeline | None = None, audit: AuditTrail | None = None, parallel: bool = True, max_iterations: int = 10, budget_limit_usd: float | None = None):
        self.agents = {a.name: a for a in agents}
        self.approval_gate = approval_gate
        self.memory = memory
        self.audit = audit or AuditTrail()
        self.parallel = parallel
        self.max_iterations = max_iterations
        self.budget_limit_usd = budget_limit_usd
        self._total_cost = 0.0

    def register_agent(self, agent: Agent) -> None:
        self.agents[agent.name] = agent

    def select_agents(self, task: str) -> list[Agent]:
        scored = [(a, a.can_handle(task)) for a in self.agents.values()]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [a for a, s in scored if s > 0.1]

    def execute(self, task: str, context: dict[str, Any] | None = None, require_approval_before: list[str] | None = None) -> ExecutionResult:
        selected = self.select_agents(task)
        if not selected:
            return ExecutionResult(task=task, status="no_agents", agents_used=[], completed_at=datetime.now(timezone.utc).isoformat())

        if self.memory:
            self.memory.working.set("current_task", task)

        all_actions: list[ActionResult] = []
        agents_used: list[str] = []

        def approval_cb(agent_name: str, action: dict[str, Any]) -> tuple[bool, str]:
            if self.approval_gate:
                return self.approval_gate.request_approval(agent_name, action)
            return True, "auto"

        for agent in selected[:self.max_iterations]:
            if self.budget_limit_usd and self._total_cost >= self.budget_limit_usd:
                logger.warning("budget_exceeded", limit=self.budget_limit_usd)
                return ExecutionResult(task=task, status="budget_exceeded", agents_used=agents_used, actions=all_actions, cost_usd=self._total_cost, completed_at=datetime.now(timezone.utc).isoformat())

            agent.reset_turn()
            actions = agent.execute(task, context, approval_callback=approval_cb)
            for a in actions:
                self._total_cost += self.COST_PER_ACTION
                self.audit.log(agent=a.agent, action=a.action, decision=a.status, approver=a.approved_by)
            all_actions.extend(actions)
            agents_used.append(agent.name)

        if self.memory:
            self.memory.after_turn({"task": task, "agents": agents_used, "outcome": "success", "steps": [a.action for a in all_actions]})

        status = "denied" if any(a.status == "denied" for a in all_actions) else "completed"
        return ExecutionResult(task=task, status=status, agents_used=agents_used, actions=all_actions, cost_usd=self._total_cost, completed_at=datetime.now(timezone.utc).isoformat())
