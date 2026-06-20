"""Example: SOC 2 Type II compliance automation with evidence collection.

This example shows how to set up a governance-focused agent that
automates SOC 2 evidence collection with policy-based access control.
"""

from harness import Agent, KnowledgeGraph
from harness.governance import ApprovalGate, PolicyEngine, PolicyRule

# 1. Build knowledge graph of compliance-relevant systems
kg = KnowledgeGraph()

kg.add_entity("aws_prod", kind="cloud_environment", attributes={
    "provider": "aws",
    "region": "us-east-1",
    "account_id": "123456789012",
    "services": ["ECS", "RDS", "S3", "CloudTrail", "GuardDuty"],
})

kg.add_entity("github_org", kind="code_repository", attributes={
    "org": "acme-corp",
    "repos": 47,
    "branch_protection": True,
    "required_reviewers": 2,
})

kg.add_entity("okta_idp", kind="identity_provider", attributes={
    "provider": "okta",
    "mfa_enforced": True,
    "sso_apps": 23,
    "user_count": 450,
})

kg.add_relation("aws_prod", "okta_idp", "authenticated_by")
kg.add_relation("github_org", "okta_idp", "authenticated_by")

# 2. Set up the compliance agent
felix = Agent(
    name="Felix",
    role="Governance & Compliance",
    skills=["policy_evaluation", "evidence_collection", "audit_reporting", "soc2_mapping"],
    knowledge_graph=kg,
)

# 3. Define policies
policy_engine = PolicyEngine()

policy_engine.add_rule(PolicyRule(
    name="require_approval_for_prod_access",
    condition=lambda ctx: ctx.get("environment") == "production",
    effect="require_approval",
    obligations=["log_access", "notify_security_team"],
))

policy_engine.add_rule(PolicyRule(
    name="deny_pii_export",
    condition=lambda ctx: ctx.get("contains_pii", False) and ctx.get("action") == "export",
    effect="deny",
))

# 4. Evaluate a sample action
print("Policy evaluation:")
result = policy_engine.evaluate({
    "environment": "production",
    "action": "read_cloudtrail_logs",
    "agent": "Felix",
})
print(f"  Effect: {result['effect']}")
print(f"  Matched rules: {result['matched_rules']}")
print(f"  Obligations: {result['obligations']}")
print()

# 5. Run compliance check with approval gate
gate = ApprovalGate(
    approvers=["ciso@acme-corp.com"],
    require_for=["evidence_collection", "audit_report_generation"],
    name="soc2-gate",
)

print("Running SOC 2 evidence collection...")
evidence_result = felix.execute(
    task="Collect SOC 2 Type II evidence for access control (CC6.1) and change management (CC8.1)",
    context={
        "framework": "SOC 2 Type II",
        "controls": ["CC6.1", "CC8.1"],
        "period": "2025-01-01 to 2025-12-31",
        "systems": ["aws_prod", "github_org", "okta_idp"],
    },
    approval_gate=gate,
)

print(f"Result: {evidence_result.output}")
print(f"Trace ID: {evidence_result.trace_id}")
