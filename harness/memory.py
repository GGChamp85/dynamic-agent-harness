"""5-layer biologically inspired memory stack for AI agents."""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class MemoryEntry:
    content: Any
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    metadata: dict[str, Any] = field(default_factory=dict)


class WorkingMemory:
    """Layer 1: In-context state for the current turn (prefrontal cortex).

    Bounded by a configurable window size. Resets at session end.
    """

    def __init__(self, max_items: int = 50) -> None:
        self.max_items = max_items
        self._buffer: deque[MemoryEntry] = deque(maxlen=max_items)

    def add(self, content: Any, **metadata: Any) -> MemoryEntry:
        entry = MemoryEntry(content=content, metadata=metadata)
        self._buffer.append(entry)
        return entry

    def get_context(self) -> list[MemoryEntry]:
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    @property
    def size(self) -> int:
        return len(self._buffer)


class EpisodicMemory:
    """Layer 2: Append-only traces of what happened across sessions (hippocampus).

    Retrieved at planning time to inform agent decisions with past experience.
    """

    def __init__(self) -> None:
        self._episodes: list[MemoryEntry] = []

    def append(self, content: Any, session_id: str | None = None, **metadata: Any) -> MemoryEntry:
        entry = MemoryEntry(content=content, metadata={"session_id": session_id, **metadata})
        self._episodes.append(entry)
        logger.debug("episodic_trace_appended", entry_id=entry.entry_id)
        return entry

    def retrieve(self, session_id: str | None = None, limit: int = 20) -> list[MemoryEntry]:
        if session_id:
            filtered = [e for e in self._episodes if e.metadata.get("session_id") == session_id]
            return filtered[-limit:]
        return self._episodes[-limit:]

    @property
    def size(self) -> int:
        return len(self._episodes)


class SemanticMemory:
    """Layer 3: Entity store of typed attributes (temporal lobe).

    Built by extraction jobs reading episodes. Supports dedup and resolution on write.
    In production, backed by a vector database (ChromaDB, Pinecone, etc.).
    """

    def __init__(self) -> None:
        self._entities: dict[str, MemoryEntry] = {}

    def store(self, entity_id: str, attributes: dict[str, Any], **metadata: Any) -> MemoryEntry:
        if entity_id in self._entities:
            existing = self._entities[entity_id]
            existing.content.update(attributes)
            existing.metadata.update(metadata)
            return existing
        entry = MemoryEntry(content=attributes, metadata=metadata)
        self._entities[entity_id] = entry
        return entry

    def retrieve(self, entity_id: str) -> MemoryEntry | None:
        return self._entities.get(entity_id)

    def search(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Semantic search across entities. In production, uses vector similarity."""
        results = []
        query_lower = query.lower()
        for eid, entry in self._entities.items():
            if query_lower in eid.lower() or query_lower in str(entry.content).lower():
                results.append(entry)
                if len(results) >= top_k:
                    break
        return results

    @property
    def size(self) -> int:
        return len(self._entities)


class ProceduralMemory:
    """Layer 4: Versioned skill registry of procedures (basal ganglia + cerebellum).

    Built by reflection passes over past episodes. In production, backed by
    a graph database (Neo4j) for versioning and dependency tracking.
    """

    def __init__(self) -> None:
        self._procedures: dict[str, list[MemoryEntry]] = {}

    def register(self, procedure_name: str, steps: list[str], version: int = 1, **metadata: Any) -> MemoryEntry:
        entry = MemoryEntry(
            content={"steps": steps, "version": version},
            metadata={"procedure_name": procedure_name, **metadata},
        )
        if procedure_name not in self._procedures:
            self._procedures[procedure_name] = []
        self._procedures[procedure_name].append(entry)
        logger.debug("procedure_registered", name=procedure_name, version=version)
        return entry

    def get_latest(self, procedure_name: str) -> MemoryEntry | None:
        versions = self._procedures.get(procedure_name, [])
        return versions[-1] if versions else None

    def list_procedures(self) -> list[str]:
        return list(self._procedures.keys())

    @property
    def size(self) -> int:
        return sum(len(v) for v in self._procedures.values())


class MetaMemory:
    """Layer 5: Governs the other four layers (anterior prefrontal cortex).

    Manages retention policies, decay, compression, dedup, and forgetting.
    Runs on schedule or when triggered by threshold conditions.
    """

    def __init__(
        self,
        max_episodic: int = 10_000,
        max_working: int = 50,
        decay_threshold_days: int = 90,
    ) -> None:
        self.max_episodic = max_episodic
        self.max_working = max_working
        self.decay_threshold_days = decay_threshold_days
        self._policies: list[dict[str, Any]] = []

    def add_policy(self, name: str, layer: str, action: str, condition: str) -> None:
        self._policies.append({
            "name": name,
            "layer": layer,
            "action": action,
            "condition": condition,
        })

    def run_maintenance(
        self,
        working: WorkingMemory,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
    ) -> dict[str, Any]:
        """Run scheduled maintenance across all memory layers."""
        report: dict[str, Any] = {"actions_taken": []}

        if episodic.size > self.max_episodic:
            overflow = episodic.size - self.max_episodic
            report["actions_taken"].append(f"episodic: flagged {overflow} entries for archival")

        report["layer_sizes"] = {
            "working": working.size,
            "episodic": episodic.size,
            "semantic": semantic.size,
            "procedural": procedural.size,
        }

        logger.info("meta_maintenance_completed", **report)
        return report


class MemoryPipeline:
    """Orchestrates the 5-layer memory stack for each agent turn.

    Runtime pipeline:
    1. User input → Working Memory (sync)
    2. LLM planning reads Episodic/Semantic/Procedural
    3. After turn: episodic trace appended (sync)
    4. Semantic extraction job (async)
    5. Procedural reflection pass (async batch)
    6. Meta-Memory maintenance (scheduled)
    """

    def __init__(self) -> None:
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.meta = MetaMemory()

    def process_turn(
        self,
        user_input: str,
        agent_response: str,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        self.working.add({"role": "user", "content": user_input})
        self.working.add({"role": "assistant", "content": agent_response})

        self.episodic.append(
            content={"input": user_input, "response": agent_response},
            session_id=session_id,
        )

        logger.info("turn_processed", working_size=self.working.size, episodic_size=self.episodic.size)

        return {
            "working_size": self.working.size,
            "episodic_size": self.episodic.size,
            "semantic_size": self.semantic.size,
            "procedural_size": self.procedural.size,
        }

    def get_planning_context(self, query: str, session_id: str | None = None) -> dict[str, Any]:
        return {
            "working": [e.content for e in self.working.get_context()],
            "recent_episodes": [e.content for e in self.episodic.retrieve(session_id=session_id, limit=10)],
            "semantic_matches": [e.content for e in self.semantic.search(query, top_k=5)],
            "procedures": self.procedural.list_procedures(),
        }
