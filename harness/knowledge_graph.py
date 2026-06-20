"""Knowledge Graph — decode your enterprise before any agent acts."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Entity:
    id: str
    type: str
    attributes: dict[str, Any] = field(default_factory=dict)

@dataclass
class Relation:
    source: str
    relation: str
    target: str
    attributes: dict[str, Any] = field(default_factory=dict)

class KnowledgeGraph:
    """In-memory knowledge graph for enterprise domain modeling."""
    def __init__(self) -> None:
        self._entities: dict[str, Entity] = {}
        self._relations: list[Relation] = []

    def add_entity(self, id: str, type: str, attributes: dict[str, Any] | None = None) -> Entity:
        entity = Entity(id=id, type=type, attributes=attributes or {})
        self._entities[id] = entity
        return entity

    def get_entity(self, id: str) -> Entity | None:
        return self._entities.get(id)

    def add_relation(self, source: str, relation: str, target: str, attributes: dict[str, Any] | None = None) -> Relation:
        rel = Relation(source=source, relation=relation, target=target, attributes=attributes or {})
        self._relations.append(rel)
        return rel

    def query(self, entity_id: str, depth: int = 1) -> dict[str, Any]:
        entity = self._entities.get(entity_id)
        if not entity:
            return {}
        result: dict[str, Any] = {"entity": {"id": entity.id, "type": entity.type, **entity.attributes}, "relations": []}
        visited = {entity_id}
        frontier = [entity_id]
        for _ in range(depth):
            next_frontier: list[str] = []
            for cid in frontier:
                for rel in self._relations:
                    if rel.source == cid and rel.target not in visited:
                        target = self._entities.get(rel.target)
                        result["relations"].append({"source": rel.source, "relation": rel.relation, "target": rel.target, "target_type": target.type if target else "unknown"})
                        visited.add(rel.target); next_frontier.append(rel.target)
                    elif rel.target == cid and rel.source not in visited:
                        source = self._entities.get(rel.source)
                        result["relations"].append({"source": rel.source, "relation": rel.relation, "target": rel.target, "source_type": source.type if source else "unknown"})
                        visited.add(rel.source); next_frontier.append(rel.source)
            frontier = next_frontier
        return result

    def find_entities(self, filters: dict[str, Any]) -> list[Entity]:
        return [e for e in self._entities.values() if all(e.attributes.get(k) == v for k, v in filters.items())]

    def impact_analysis(self, entity_id: str, depth: int = 3) -> dict[str, Any]:
        result = self.query(entity_id, depth=depth)
        dependents = [r for r in self._relations if r.target == entity_id and r.relation in ("depends_on", "reads_from", "calls")]
        return {**result, "direct_dependents": len(dependents), "total_in_blast_radius": len(result.get("relations", [])) + 1, "dependent_services": [{"id": d.source, "relation": d.relation} for d in dependents]}

    def decode_enterprise(self) -> dict[str, Any]:
        types: dict[str, int] = {}
        for e in self._entities.values():
            types[e.type] = types.get(e.type, 0) + 1
        return {"total_entities": len(self._entities), "total_relations": len(self._relations), "entity_types": types}

    def __len__(self) -> int:
        return len(self._entities)

    def __repr__(self) -> str:
        return f"KnowledgeGraph(entities={len(self._entities)}, relations={len(self._relations)})"
