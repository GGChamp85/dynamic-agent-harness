"""Example: Legacy database migration with schema analysis and parity verification.

This example shows how to set up an agent that migrates a PostgreSQL
database to Snowflake, with human approval gates at every critical step.
"""

from harness import Agent, KnowledgeGraph
from harness.governance import ApprovalGate

# 1. Build the knowledge graph from enterprise sources
kg = KnowledgeGraph()

kg.add_entity("users", kind="database_table", attributes={
    "columns": ["id", "name", "email", "created_at", "updated_at"],
    "row_count": 2_400_000,
    "database": "postgres_prod",
    "schema": "public",
})

kg.add_entity("orders", kind="database_table", attributes={
    "columns": ["id", "user_id", "total", "status", "created_at"],
    "row_count": 8_700_000,
    "database": "postgres_prod",
    "schema": "public",
})

kg.add_entity("snowflake_dwh", kind="database", attributes={
    "provider": "snowflake",
    "warehouse": "COMPUTE_WH",
    "target_schema": "RAW",
})

kg.add_relation("orders", "users", "references", attributes={"column": "user_id"})

# 2. Create the migration agent
atlas = Agent(
    name="Atlas",
    role="Code & Data Migration",
    skills=["schema_analysis", "data_migration", "parity_verification"],
    knowledge_graph=kg,
)

# 3. Set up human approval for destructive operations
gate = ApprovalGate(
    approvers=["gaurav@vouchstone.ai", "anand@vouchstone.ai"],
    require_for=["schema_change", "data_mutation", "production_deploy"],
    name="migration-approval",
)

# 4. Execute the migration
print("Starting migration...")
print(f"Knowledge graph: {kg.stats()}")
print()

result = atlas.execute(
    task="Migrate users and orders tables from PostgreSQL to Snowflake DWH",
    context={
        "source": "postgres_prod",
        "target": "snowflake_dwh",
        "tables": ["users", "orders"],
        "strategy": "full_load_then_cdc",
    },
    approval_gate=gate,
)

print(f"Result: {result.output}")
print(f"Approved by: {result.approved_by}")
print(f"Trace ID: {result.trace_id}")
print()

# 5. Review the audit trail
print("Audit trail:")
for entry in atlas.audit_trail.export():
    print(f"  [{entry['timestamp']}] {entry['event']} — {entry['details']}")
