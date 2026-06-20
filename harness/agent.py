"""Base Agent class for supervised AI agents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from harness.governance import ApprovalGate, AuditTrail
from harness.knowledge_graph import KnowledgeGraph

logger = structlog.get_logger()


@dataclass
class AgentResult:
    agent_name: str
    task: str
    output: Any
    approved_by: str | None = None
    trace_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


class Agent:
    """A supervised AI agent with domain context and human governance.

    Each agent has a name, role, skill set, and optional reference to
    the enterprise knowledge graph. All consequential actions pass
    through an approval gate before execution.
    """

    def __init__(
        self,
        name: str,
        role: str,
        skills: list[str] | None = None,
        knowledge_graph: KnowledgeGraph | None = None,
        llm_provider: str = "anthropic",
        model: str = "claude-sonnet-4-6",
    ) -> None:
        self.name = name
        self.role = role
        self.skills = skills or []
        self.knowledge_graph = knowledge_graph
        self.llm_provider = llm_provider
        self.model = model
        self.audit_trail = AuditTrail(agent_name=name)
        self._tools: dict[str, Callable[..., Any]] = {}

    def register_tool(self, name: str, fn: Callable[..., Any]) -> None:
        self._tools[name] = fn
        logger.info("tool_registered", agent=self.name, tool=name)

    def query_knowledge(self, **filters: Any) -> list[Any]:
        if self.knowledge_graph is None:
            raise RuntimeError(f"Agent '{self.name}' has no knowledge graph attached")
        return self.knowledge_graph.query(**filters)

    def execute(
        self,
        task: str,
        context: dict[str, Any] | None = None,
        approval_gate: ApprovalGate | None = None,
    ) -> AgentResult:
        trace_id = uuid.uuid4().hex[:12]
        log = logger.bind(agent=self.name, task=task, trace_id=trace_id)

        log.info("execution_started")
        self.audit_trail.log("execution_started", task=task, trace_id=trace_id)

        kg_context = {}
        if self.knowledge_graph:
            kg_context = {"entities": len(self.knowledge_graph.entities)}
            log.info("knowledge_graph_loaded", entity_count=kg_context["entities"])

        approved_by = None
        if approval_gate:
            log.info("awaiting_approval", approvers=approval_gate.approvers)
            self.audit_trail.log("approval_requested", gate=approval_gate.name)
            approved_by = approval_gate.request_approval(
                agent=self.name,
                action=task,
                context=context or {},
            )
            self.audit_trail.log("approval_granted", approved_by=approved_by)
            log.info("approval_granted", approved_by=approved_by)

        output = self._plan_and_act(task, context or {}, kg_context)

        self.audit_trail.log("execution_completed", trace_id=trace_id, output_type=type(output).__name__)
        log.info("execution_completed")

        return AgentResult(
            agent_name=self.name,
            task=task,
            output=output,
            approved_by=approved_by,
            trace_id=trace_id,
        )

    def _plan_and_act(self, task: str, context: dict[str, Any], kg_context: dict[str, Any]) -> Any:
        """Plan execution steps and act on them. Override for custom behavior."""
        return {
            "status": "completed",
            "task": task,
            "agent": self.name,
            "context_keys": list(context.keys()),
            "kg_entities": kg_context.get("entities", 0),
        }

    def has_skill(self, skill: str) -> bool:
        return skill in self.skills

    def __repr__(self) -> str:
        return f"Agent(name={self.name!r}, role={self.role!r}, skills={self.skills})"
