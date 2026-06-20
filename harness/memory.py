"""5-Layer Memory Stack — biologically-inspired memory for persistent agent intelligence."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

class WorkingMemory:
    """Layer 1: In-context state for the current turn. Analogous to prefrontal cortex."""
    def __init__(self, backend: str | None = None, max_entries: int = 100):
        self.backend = backend
        self.max_entries = max_entries
        self._store: dict[str, Any] = {}
    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self.max_entries:
            oldest = next(iter(self._store))
            del self._store[oldest]
        self._store[key] = value
    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(key, default)
    def clear(self) -> None:
        self._store.clear()
    @property
    def size(self) -> int:
        return len(self._store)

class EpisodicMemory:
    """Layer 2: Append-only traces across sessions. Analogous to hippocampus."""
    def __init__(self, backend: str | None = None):
        self.backend = backend
        self._traces: list[dict[str, Any]] = []
    def append(self, trace: dict[str, Any]) -> int:
        self._traces.append(trace)
        return len(self._traces) - 1
    def recall(self, task: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        if task:
            matches = [t for t in self._traces if task.lower() in str(t).lower()]
            return matches[-limit:]
        return self._traces[-limit:]
    @property
    def count(self) -> int:
        return len(self._traces)

class SemanticMemory:
    """Layer 3: Entity store of typed attributes. Analogous to temporal lobe."""
    def __init__(self, backend: str | None = None):
        self.backend = backend
        self._entities: dict[str, dict[str, Any]] = {}
    def store(self, entity_id: str, attributes: dict[str, Any]) -> None:
        if entity_id in self._entities:
            self._entities[entity_id].update(attributes)
        else:
            self._entities[entity_id] = dict(attributes)
    def retrieve(self, entity_id: str) -> dict[str, Any] | None:
        return self._entities.get(entity_id)
    def search(self, query: str, limit: int = 10) -> list[tuple[str, dict[str, Any]]]:
        q = query.lower()
        return [(eid, a) for eid, a in self._entities.items() if q in eid.lower() or q in str(a).lower()][:limit]
    @property
    def count(self) -> int:
        return len(self._entities)

@dataclass
class Skill:
    name: str
    steps: list[str]
    success_rate: float = 0.0
    version: int = 1
    usage_count: int = 0

class ProceduralMemory:
    """Layer 4: Versioned skill registry. Analogous to basal ganglia + cerebellum."""
    def __init__(self, backend: str | None = None):
        self.backend = backend
        self._skills: dict[str, Skill] = {}
    def register_skill(self, name: str, steps: list[str], success_rate: float = 0.0) -> Skill:
        if name in self._skills:
            s = self._skills[name]
            s.steps = steps; s.success_rate = success_rate; s.version += 1
            return s
        skill = Skill(name=name, steps=steps, success_rate=success_rate)
        self._skills[name] = skill
        return skill
    def get_skill(self, name: str) -> Skill | None:
        return self._skills.get(name)
    def best_skill_for(self, task: str) -> Skill | None:
        task_lower = task.lower()
        candidates = [s for s in self._skills.values() if any(w in task_lower for w in s.name.lower().split("-"))]
        return max(candidates, key=lambda s: s.success_rate) if candidates else None
    @property
    def count(self) -> int:
        return len(self._skills)

class MetaMemory:
    """Layer 5: Governs the other four. Analogous to anterior prefrontal cortex."""
    def __init__(self, working: WorkingMemory | None = None, episodic: EpisodicMemory | None = None, semantic: SemanticMemory | None = None, procedural: ProceduralMemory | None = None):
        self._working = working; self._episodic = episodic; self._semantic = semantic; self._procedural = procedural
        self._maintenance_runs = 0
    def run_maintenance(self) -> dict[str, Any]:
        report: dict[str, Any] = {"actions": []}
        if self._working and self._working.size > self._working.max_entries * 0.9:
            self._working.clear(); report["actions"].append("working_memory_cleared")
        if self._episodic and self._episodic.count > 1000:
            report["actions"].append(f"episodic_has_{self._episodic.count}_traces")
        if self._procedural:
            for s in self._procedural._skills.values():
                if s.success_rate < 0.3 and s.usage_count > 5:
                    report["actions"].append(f"deprecate_{s.name}")
        self._maintenance_runs += 1; report["run"] = self._maintenance_runs
        return report

class MemoryPipeline:
    """Orchestrates all 5 memory layers."""
    def __init__(self, working_backend: str | None = None, episodic_backend: str | None = None, semantic_backend: str | None = None, procedural_backend: str | None = None):
        self.working = WorkingMemory(backend=working_backend)
        self.episodic = EpisodicMemory(backend=episodic_backend)
        self.semantic = SemanticMemory(backend=semantic_backend)
        self.procedural = ProceduralMemory(backend=procedural_backend)
        self.meta = MetaMemory(working=self.working, episodic=self.episodic, semantic=self.semantic, procedural=self.procedural)
    def after_turn(self, trace: dict[str, Any]) -> None:
        self.episodic.append(trace)
        for eid, attrs in trace.get("entities_observed", {}).items():
            self.semantic.store(eid, attrs)
        if trace.get("outcome") == "success" and trace.get("steps"):
            task = trace.get("task", "unnamed")
            existing = self.procedural.get_skill(task)
            rate = existing.success_rate * 0.9 + 0.1 if existing else 0.5
            self.procedural.register_skill(task, trace["steps"], success_rate=rate)
