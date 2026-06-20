# Dynamic Agent Harness

**Production-ready framework for building, deploying, and governing supervised AI agents with human-in-the-loop sign-off.**

Built by [Vouchstone](https://vouchstone.ai) — Accountable AI delivery for the enterprise.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Patent](https://img.shields.io/badge/US_Patent-12%2C536%2C365-orange.svg)](https://patents.google.com/patent/US12536365)

---

## Why This Exists

Enterprise AI fails without governance. Most agent frameworks let AI act autonomously — but enterprises need:

- **Named human sign-off** on every consequential action
- **Domain-decoded knowledge** before agents act
- **Tamper-evident audit trails** for compliance
- **Budget controls** that auto-pause before overspend

The Dynamic Agent Harness solves this. It's the open-source foundation behind Vouchstone's delivery pods.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    ORCHESTRATOR                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │  Agent A  │  │  Agent B  │  │  Agent C  │  ...        │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘               │
│       │              │              │                     │
│  ┌────┴──────────────┴──────────────┴────┐               │
│  │         GOVERNANCE LAYER              │               │
│  │  ┌────────┐ ┌────────┐ ┌───────────┐  │               │
│  │  │ Policy │ │ Audit  │ │ Approval  │  │               │
│  │  │ Engine │ │ Trail  │ │   Gate    │  │               │
│  │  └────────┘ └────────┘ └───────────┘  │               │
│  └───────────────────┬───────────────────┘               │
│                      │                                   │
│  ┌───────────────────┴───────────────────┐               │
│  │         5-LAYER MEMORY STACK          │               │
│  │  Working → Episodic → Semantic →      │               │
│  │  Procedural → Meta-Memory             │               │
│  └───────────────────┬───────────────────┘               │
│                      │                                   │
│  ┌───────────────────┴───────────────────┐               │
│  │        KNOWLEDGE GRAPH                │               │
│  │  Entities · Relations · Queries       │               │
│  └───────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────┘
```

## Quick Start

### Installation

```bash
pip install dynamic-agent-harness
```

Or from source:

```bash
git clone https://github.com/GGChamp85/dynamic-agent-harness.git
cd dynamic-agent-harness
pip install -e .
```

### Basic Usage

```python
from harness import Agent, Orchestrator, KnowledgeGraph
from harness.governance import ApprovalGate

# 1. Build your knowledge graph
kg = KnowledgeGraph()
kg.add_entity("payments-service", "microservice", {
    "language": "Java",
    "database": "PostgreSQL",
    "owner": "platform-team"
})
kg.add_entity("orders-service", "microservice", {
    "language": "Python",
    "database": "MongoDB",
    "owner": "commerce-team"
})
kg.add_relation("payments-service", "depends_on", "orders-service")

# 2. Define agents with domain context
migration_agent = Agent(
    name="Atlas",
    role="Code & Data Migration",
    skills=["schema-migration", "data-validation", "rollback-planning"],
    knowledge_graph=kg
)

governance_agent = Agent(
    name="Felix",
    role="Governance & Compliance",
    skills=["policy-check", "audit-logging", "risk-assessment"],
    knowledge_graph=kg
)

# 3. Set up human approval gates
gate = ApprovalGate(
    approvers=["lead@company.com"],
    require_for=["production-deploy", "schema-change", "data-deletion"]
)

# 4. Orchestrate
orchestrator = Orchestrator(
    agents=[migration_agent, governance_agent],
    approval_gate=gate
)

result = orchestrator.execute(
    task="Migrate payments-service from Java 11 to Java 21",
    context=kg.query("payments-service")
)
```

### Multi-Agent Pod

```python
from harness import Agent, Orchestrator
from harness.governance import ApprovalGate
from harness.memory import MemoryPipeline

pod = Orchestrator(
    agents=[
        Agent("Atlas", "Code & Data", ["migration", "refactoring", "testing"]),
        Agent("Marcus", "Infra & Cloud", ["terraform", "k8s", "ci-cd"]),
        Agent("Maya", "Customer & Ops", ["runbooks", "monitoring", "alerting"]),
        Agent("Felix", "Governance", ["policy", "audit", "compliance"]),
        Agent("Priya", "Vendor & Contract", ["vendor-risk", "sla-tracking"]),
        Agent("Vega", "Financial", ["budgeting", "cost-optimization"]),
    ],
    approval_gate=ApprovalGate(approvers=["lead@company.com"]),
    memory=MemoryPipeline(),
)

result = pod.execute("Migrate ERP from on-prem Oracle to cloud-native")
```

## Core Components

### Agent

Base class for supervised AI agents with built-in governance hooks.

```python
agent = Agent(
    name="Atlas",
    role="Code & Data Migration",
    skills=["schema-migration", "data-validation"],
    knowledge_graph=kg,
    model="claude-sonnet-4-6",
    max_actions_per_turn=5
)
```

### Knowledge Graph

Decode your enterprise before any agent acts.

```python
kg = KnowledgeGraph()
kg.add_entity("user-service", "microservice", {"language": "Go", "team": "identity"})
kg.add_entity("auth-db", "database", {"engine": "PostgreSQL", "pii": True})
kg.add_relation("user-service", "reads_from", "auth-db")

deps = kg.query("user-service", depth=2)
pii_systems = kg.find_entities({"pii": True})
impact = kg.impact_analysis("auth-db")
```

### Governance

Every consequential action requires human sign-off.

```python
from harness.governance import ApprovalGate, PolicyEngine, AuditTrail

gate = ApprovalGate(
    approvers=["cto@company.com"],
    require_for=["production-deploy", "data-deletion"],
    timeout_hours=24
)

policies = PolicyEngine()
policies.add_rule("no-prod-without-tests", 
    condition=lambda a: a.target == "production",
    requirement="test_coverage >= 80%")

audit = AuditTrail(storage="postgresql://localhost/audit")
```

### 5-Layer Memory Stack

Biologically-inspired memory for persistent agent intelligence.

```python
from harness.memory import MemoryPipeline

memory = MemoryPipeline(
    working_backend="redis://localhost:6379",
    episodic_backend="postgresql://localhost:5432/memory",
    semantic_backend="chromadb://localhost:8000",
    procedural_backend="neo4j://localhost:7687",
)

memory.working.set("current_task", "Migrate payments schema")
memory.episodic.append(trace={"task": "migration", "outcome": "success"})
memory.semantic.store("payments-service", {"risk_score": 0.3})
memory.procedural.register_skill("zero-downtime-migration", steps=[...], success_rate=0.95)
memory.meta.run_maintenance()
```

## Examples

| Example | Description |
|---------|-------------|
| [`migration_agent.py`](examples/migration_agent.py) | Legacy system migration with rollback planning |
| [`compliance_agent.py`](examples/compliance_agent.py) | SOC 2 compliance audit automation |
| [`multi_agent_pod.py`](examples/multi_agent_pod.py) | Full pod orchestration with 6 agents |

## Configuration

```yaml
# harness.yaml
orchestrator:
  max_iterations: 10
  parallel: true
  budget_limit_usd: 500

agents:
  default_model: claude-sonnet-4-6
  max_actions_per_turn: 5

governance:
  require_approval: true
  approval_timeout_hours: 24
  audit_backend: postgresql://localhost/audit

memory:
  working: redis://localhost:6379
  episodic: postgresql://localhost/memory
  semantic: chromadb://localhost:8000
  procedural: neo4j://localhost:7687

knowledge_graph:
  backend: neo4j://localhost:7687
  auto_decode: true
```

## Patent

This framework implements methods covered by [US Patent 12,536,365](https://patents.google.com/patent/US12536365) — *System and method for enterprise AI agent orchestration with human-in-the-loop governance*.

## License

Apache License 2.0 — see [LICENSE](LICENSE).

## Links

- [Vouchstone Platform](https://vouchstone.ai)
- [Documentation](https://vouchstone.ai/docs)
- [Blog](https://vouchstone.ai/blog)

---

Built with conviction by the [Vouchstone](https://vouchstone.ai) team.
