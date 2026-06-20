"""Example: Full pod with orchestrator, multiple agents, and human lead.

This example shows how to set up a complete pod — human architects plus
specialized AI agents — and dispatch parallel tasks with sync barriers.
"""

from harness import Agent, KnowledgeGraph, Orchestrator
from harness.governance import ApprovalGate
from harness.memory import MemoryPipeline

# 1. Build the shared knowledge graph
kg = KnowledgeGraph()

kg.add_entity("monolith_api", kind="service", attributes={
    "language": "java",
    "framework": "spring_boot",
    "endpoints": 142,
    "loc": 85_000,
})

kg.add_entity("user_service", kind="service", attributes={
    "language": "python",
    "framework": "fastapi",
    "status": "target",
})

kg.add_entity("order_service", kind="service", attributes={
    "language": "python",
    "framework": "fastapi",
    "status": "target",
})

kg.add_entity("main_db", kind="database_table", attributes={
    "engine": "postgresql",
    "tables": 67,
    "row_count_total": 42_000_000,
})

kg.add_relation("monolith_api", "main_db", "reads_from")
kg.add_relation("user_service", "main_db", "reads_from")
kg.add_relation("order_service", "main_db", "reads_from")

print(f"Knowledge graph loaded: {kg.stats()}")
print()

# 2. Create specialized agents
atlas = Agent(
    name="Atlas",
    role="Code & Data Migration",
    skills=["schema_analysis", "data_migration", "code_decomposition", "api_mapping"],
    knowledge_graph=kg,
)

marcus = Agent(
    name="Marcus",
    role="Infrastructure & Cloud",
    skills=["terraform", "kubernetes", "ci_cd", "monitoring", "cloud_architecture"],
    knowledge_graph=kg,
)

felix = Agent(
    name="Felix",
    role="Governance & Compliance",
    skills=["policy_evaluation", "evidence_collection", "security_review", "audit_reporting"],
    knowledge_graph=kg,
)

# 3. Set up the orchestrator
orch = Orchestrator(max_workers=3)
orch.register(atlas)
orch.register(marcus)
orch.register(felix)

# 4. Set up approval gates
architecture_gate = ApprovalGate(
    approvers=["gaurav@vouchstone.ai"],
    require_for=["schema_change", "api_contract_change"],
    name="architecture-review",
)

deploy_gate = ApprovalGate(
    approvers=["gaurav@vouchstone.ai", "anand@vouchstone.ai"],
    require_for=["production_deploy", "data_mutation"],
    name="deploy-approval",
)

# 5. Dispatch parallel tasks — agents work concurrently
print("Dispatching parallel analysis tasks...")
analysis_result = orch.dispatch_parallel([
    {
        "task": "Analyze monolith_api and identify bounded contexts for user_service extraction",
        "skills_required": ["code_decomposition", "api_mapping"],
    },
    {
        "task": "Design Kubernetes deployment topology for user_service and order_service",
        "skills_required": ["kubernetes", "cloud_architecture"],
    },
    {
        "task": "Review monolith_api for security vulnerabilities and compliance gaps before migration",
        "skills_required": ["security_review", "policy_evaluation"],
    },
])

print(f"Parallel run {analysis_result.run_id}:")
print(f"  Succeeded: {len(analysis_result.results)}")
print(f"  Failed: {len(analysis_result.failed)}")
print()

for result in analysis_result.results:
    print(f"  Agent: {result.agent_name}")
    print(f"  Task: {result.task}")
    print(f"  Trace: {result.trace_id}")
    print()

# 6. Sequential tasks with approval gates
print("Running sequential migration with human sign-off...")
migration_result = orch.dispatch_sequential([
    {
        "task": "Extract user domain from monolith and create user_service schema",
        "skills_required": ["schema_analysis", "data_migration"],
        "approval_gate": architecture_gate,
    },
    {
        "task": "Set up CI/CD pipeline and staging environment for user_service",
        "skills_required": ["ci_cd", "kubernetes"],
    },
    {
        "task": "Run compliance check on user_service before production deploy",
        "skills_required": ["policy_evaluation", "evidence_collection"],
        "approval_gate": deploy_gate,
    },
])

print(f"Sequential run {migration_result.run_id}:")
print(f"  Succeeded: {len(migration_result.results)}")
print()

# 7. Memory pipeline tracks everything
memory = MemoryPipeline()
for result in analysis_result.results:
    memory.process_turn(
        user_input=result.task,
        agent_response=str(result.output),
        session_id="pod-session-001",
    )

context = memory.get_planning_context("migration progress", session_id="pod-session-001")
print(f"Memory state:")
print(f"  Working memory: {context['working'][-1] if context['working'] else 'empty'}")
print(f"  Recent episodes: {len(context['recent_episodes'])}")
print(f"  Procedures: {context['procedures']}")
