"""Multi-agent orchestrator with parallel execution and sync barriers."""

from __future__ import annotations

import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any

import structlog

from harness.agent import Agent, AgentResult
from harness.governance import ApprovalGate

logger = structlog.get_logger()


@dataclass
class TaskSpec:
    task: str
    skills_required: list[str] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)
    approval_gate: ApprovalGate | None = None


@dataclass
class OrchestratorResult:
    run_id: str
    results: list[AgentResult]
    failed: list[dict[str, Any]]


class Orchestrator:
    """Coordinates multiple agents, dispatches tasks, manages parallel execution."""

    def __init__(self, max_workers: int = 4) -> None:
        self.agents: dict[str, Agent] = {}
        self.max_workers = max_workers
        self._run_history: list[OrchestratorResult] = []

    def register(self, agent: Agent) -> None:
        self.agents[agent.name] = agent
        logger.info("agent_registered", agent=agent.name, skills=agent.skills)

    def unregister(self, name: str) -> None:
        self.agents.pop(name, None)

    def find_agent(self, skills_required: list[str]) -> Agent | None:
        best_match: Agent | None = None
        best_score = 0
        for agent in self.agents.values():
            score = sum(1 for s in skills_required if agent.has_skill(s))
            if score > best_score:
                best_score = score
                best_match = agent
        return best_match

    def dispatch(self, spec: TaskSpec) -> AgentResult:
        agent = self.find_agent(spec.skills_required)
        if agent is None:
            raise RuntimeError(f"No agent found with skills: {spec.skills_required}")
        return agent.execute(
            task=spec.task,
            context=spec.context,
            approval_gate=spec.approval_gate,
        )

    def dispatch_parallel(
        self,
        specs: list[dict[str, Any] | TaskSpec],
        barrier: bool = True,
    ) -> OrchestratorResult:
        run_id = uuid.uuid4().hex[:12]
        log = logger.bind(run_id=run_id, task_count=len(specs))
        log.info("parallel_dispatch_started")

        task_specs = [
            s if isinstance(s, TaskSpec) else TaskSpec(**s)
            for s in specs
        ]

        results: list[AgentResult] = []
        failed: list[dict[str, Any]] = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures = {
                pool.submit(self.dispatch, spec): spec
                for spec in task_specs
            }
            for future in as_completed(futures):
                spec = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    log.info("task_completed", task=spec.task, agent=result.agent_name)
                except Exception as exc:
                    failed.append({"task": spec.task, "error": str(exc)})
                    log.error("task_failed", task=spec.task, error=str(exc))

        orch_result = OrchestratorResult(run_id=run_id, results=results, failed=failed)
        self._run_history.append(orch_result)
        log.info("parallel_dispatch_completed", succeeded=len(results), failed=len(failed))
        return orch_result

    def dispatch_sequential(self, specs: list[dict[str, Any] | TaskSpec]) -> OrchestratorResult:
        run_id = uuid.uuid4().hex[:12]
        results: list[AgentResult] = []
        failed: list[dict[str, Any]] = []

        for s in specs:
            spec = s if isinstance(s, TaskSpec) else TaskSpec(**s)
            try:
                result = self.dispatch(spec)
                results.append(result)
            except Exception as exc:
                failed.append({"task": spec.task, "error": str(exc)})

        orch_result = OrchestratorResult(run_id=run_id, results=results, failed=failed)
        self._run_history.append(orch_result)
        return orch_result

    @property
    def history(self) -> list[OrchestratorResult]:
        return list(self._run_history)
