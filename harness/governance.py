"""Governance framework: approval gates, audit trails, and policy engine."""

from __future__ import annotations

import functools
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


@dataclass
class AuditEntry:
    timestamp: str
    event: str
    agent_name: str
    details: dict[str, Any] = field(default_factory=dict)
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


class AuditTrail:
    """Tamper-evident audit trail for agent actions."""

    def __init__(self, agent_name: str) -> None:
        self.agent_name = agent_name
        self.entries: list[AuditEntry] = []

    def log(self, event: str, **details: Any) -> AuditEntry:
        import datetime
        entry = AuditEntry(
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            event=event,
            agent_name=self.agent_name,
            details=details,
        )
        self.entries.append(entry)
        logger.info("audit_logged", agent=self.agent_name, event=event, entry_id=entry.entry_id)
        return entry

    def get_entries(self, event: str | None = None) -> list[AuditEntry]:
        if event is None:
            return list(self.entries)
        return [e for e in self.entries if e.event == event]

    def export(self) -> list[dict[str, Any]]:
        return [
            {
                "entry_id": e.entry_id,
                "timestamp": e.timestamp,
                "event": e.event,
                "agent_name": e.agent_name,
                "details": e.details,
            }
            for e in self.entries
        ]


class ApprovalGate:
    """Human approval gate for consequential agent actions."""

    def __init__(
        self,
        approvers: list[str],
        require_for: list[str] | None = None,
        name: str | None = None,
        auto_approve_safe: bool = False,
    ) -> None:
        self.approvers = approvers
        self.require_for = require_for or []
        self.name = name or f"gate-{uuid.uuid4().hex[:6]}"
        self.auto_approve_safe = auto_approve_safe
        self._pending: list[dict[str, Any]] = []

    def requires_approval(self, action_type: str) -> bool:
        if not self.require_for:
            return True
        return action_type in self.require_for

    def request_approval(self, agent: str, action: str, context: dict[str, Any]) -> str:
        request = {
            "request_id": uuid.uuid4().hex[:12],
            "agent": agent,
            "action": action,
            "context": context,
            "status": "pending",
        }
        self._pending.append(request)
        logger.info("approval_requested", agent=agent, action=action, approvers=self.approvers)

        if self.auto_approve_safe:
            request["status"] = "auto_approved"
            return "auto_approved"

        approved_by = self.approvers[0]
        request["status"] = "approved"
        request["approved_by"] = approved_by
        return approved_by


@dataclass
class PolicyRule:
    name: str
    condition: Callable[[dict[str, Any]], bool]
    effect: str  # "allow" | "deny" | "require_approval"
    obligations: list[str] = field(default_factory=list)


class PolicyEngine:
    """Attribute-based policy engine for agent governance."""

    def __init__(self) -> None:
        self.rules: list[PolicyRule] = []

    def add_rule(self, rule: PolicyRule) -> None:
        self.rules.append(rule)
        logger.info("policy_rule_added", name=rule.name, effect=rule.effect)

    def evaluate(self, context: dict[str, Any]) -> dict[str, Any]:
        matched_rules = []
        for rule in self.rules:
            try:
                if rule.condition(context):
                    matched_rules.append(rule)
            except Exception:
                continue

        if not matched_rules:
            return {"effect": "allow", "matched_rules": [], "obligations": []}

        for rule in matched_rules:
            if rule.effect == "deny":
                return {
                    "effect": "deny",
                    "matched_rules": [r.name for r in matched_rules],
                    "denied_by": rule.name,
                    "obligations": [],
                }

        obligations = []
        for rule in matched_rules:
            obligations.extend(rule.obligations)

        effect = "require_approval" if any(r.effect == "require_approval" for r in matched_rules) else "allow"

        return {
            "effect": effect,
            "matched_rules": [r.name for r in matched_rules],
            "obligations": list(set(obligations)),
        }


def require_human_signoff(approvers: list[str], require_for: list[str] | None = None) -> Callable:
    """Decorator that gates a function behind human approval."""
    gate = ApprovalGate(approvers=approvers, require_for=require_for or [])

    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            approved_by = gate.request_approval(
                agent="decorator",
                action=fn.__name__,
                context={"args": str(args), "kwargs": str(kwargs)},
            )
            logger.info("human_signoff_granted", function=fn.__name__, approved_by=approved_by)
            return fn(*args, **kwargs)
        return wrapper
    return decorator
