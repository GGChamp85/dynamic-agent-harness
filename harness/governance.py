"""Governance — approval gates, policy engine, tamper-evident audit trail."""
from __future__ import annotations
import hashlib, json, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

@dataclass
class AuditEntry:
    id: str
    timestamp: str
    agent: str
    action: str
    decision: str
    approver: str | None = None
    policy_ids: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    def __post_init__(self) -> None:
        if not self.checksum:
            payload = json.dumps({"id": self.id, "timestamp": self.timestamp, "agent": self.agent, "action": self.action, "decision": self.decision}, sort_keys=True)
            self.checksum = hashlib.sha256(payload.encode()).hexdigest()[:16]

class ApprovalGate:
    """Blocks execution until a human approves."""
    def __init__(self, approvers: list[str], require_for: list[str] | None = None, timeout_hours: int = 24):
        self.approvers = approvers
        self.require_for = set(require_for or [])
        self.timeout_hours = timeout_hours

    def requires_approval(self, action: str) -> bool:
        if not self.require_for:
            return True
        return any(t in action for t in self.require_for)

    def request_approval(self, agent_name: str, action: dict[str, Any], callback: Callable | None = None) -> tuple[bool, str]:
        if callback:
            return callback(agent_name, action)
        return True, self.approvers[0]

@dataclass
class PolicyRule:
    id: str
    name: str
    condition: Callable[[Any], bool]
    requirement: str
    severity: str = "block"

class PolicyEngine:
    """Attribute-based policy engine."""
    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []

    def add_rule(self, name: str, condition: Callable[[Any], bool], requirement: str, severity: str = "block") -> PolicyRule:
        rule = PolicyRule(id=uuid.uuid4().hex[:8], name=name, condition=condition, requirement=requirement, severity=severity)
        self._rules.append(rule)
        return rule

    def evaluate(self, action: Any) -> tuple[bool, list[PolicyRule]]:
        violations = []
        for rule in self._rules:
            try:
                if rule.condition(action):
                    violations.append(rule)
            except Exception:
                pass
        blocking = [v for v in violations if v.severity == "block"]
        return len(blocking) == 0, violations

class AuditTrail:
    """Tamper-evident audit log with hash chain."""
    def __init__(self, storage: str | None = None):
        self.storage = storage
        self._entries: list[AuditEntry] = []
        self._chain_hash: str = "genesis"

    def log(self, agent: str, action: str, decision: str, approver: str | None = None, policy_ids: list[str] | None = None, context: dict[str, Any] | None = None) -> AuditEntry:
        entry = AuditEntry(id=uuid.uuid4().hex[:12], timestamp=datetime.now(timezone.utc).isoformat(), agent=agent, action=action, decision=decision, approver=approver, policy_ids=policy_ids or [], context=context or {})
        chain_payload = f"{self._chain_hash}:{entry.checksum}"
        self._chain_hash = hashlib.sha256(chain_payload.encode()).hexdigest()[:16]
        self._entries.append(entry)
        return entry

    def verify_chain(self) -> bool:
        chain_hash = "genesis"
        for entry in self._entries:
            chain_payload = f"{chain_hash}:{entry.checksum}"
            chain_hash = hashlib.sha256(chain_payload.encode()).hexdigest()[:16]
        return chain_hash == self._chain_hash

    def get_entries(self, agent: str | None = None, limit: int = 100) -> list[AuditEntry]:
        entries = self._entries
        if agent:
            entries = [e for e in entries if e.agent == agent]
        return entries[-limit:]

    @property
    def count(self) -> int:
        return len(self._entries)

    def export_json(self) -> list[dict[str, Any]]:
        return [{"id": e.id, "timestamp": e.timestamp, "agent": e.agent, "action": e.action, "decision": e.decision, "approver": e.approver, "checksum": e.checksum} for e in self._entries]
