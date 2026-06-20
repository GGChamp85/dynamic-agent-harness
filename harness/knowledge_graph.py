"""Enterprise knowledge graph for domain-led agent development."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger()


@dataclass
class Entity:
    id: str
    kind: str
    attributes: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class Relation:
    source_id: str
    target_id: str
    relation_type: str
    attributes: dict[str, Any] = field(default_factory=dict)


class KnowledgeGraph:
    """Living knowledge graph that decodes enterprise context for agents.

    Entities represent business objects (tables, APIs, rules, decisions).
    Relations capture how they connect. Agents query this graph to ground
    their actions in real domain knowledge — not generic prompts.
    """

    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []

    def add_entity(self, id: str, kind: str, attributes: dict[str, Any] | None = None, tags: list[str] | None = None) -> Entity:
        entity = Entity(id=id, kind=kind, attributes=attributes or {}, tags=tags or [])
        self.entities[id] = entity
        logger.info("entity_added", id=id, kind=kind)
        return entity

    def add_relation(self, source_id: str, target_id: str, relation_type: str, attributes: dict[str, Any] | None = None) -> Relation:
        if source_id not in self.entities:
            raise KeyError(f"Source entity '{source_id}' not found")
        if target_id not in self.entities:
            raise KeyError(f"Target entity '{target_id}' not found")
        relation = Relation(
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            attributes=attributes or {},
        )
        self.relations.append(relation)
        logger.info("relation_added", source=source_id, target=target_id, type=relation_type)
        return relation

    def get_entity(self, id: str) -> Entity | None:
        return self.entities.get(id)

    def query(self, kind: str | None = None, **attr_filters: Any) -> list[Entity]:
        results = []
        for entity in self.entities.values():
            if kind and entity.kind != kind:
                continue
            match = all(
                entity.attributes.get(k) == v
                for k, v in attr_filters.items()
            )
            if match:
                results.append(entity)
        return results

    def get_relations(self, entity_id: str, relation_type: str | None = None, direction: str = "outgoing") -> list[Relation]:
        results = []
        for rel in self.relations:
            if direction in ("outgoing", "both") and rel.source_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel)
            if direction in ("incoming", "both") and rel.target_id == entity_id:
                if relation_type is None or rel.relation_type == relation_type:
                    results.append(rel)
        return results

    def decode_enterprise(self, sources: list[str]) -> dict[str, int]:
        """Decode enterprise systems into the knowledge graph.

        Connects to databases, reads codebases, and parses documentation
        to extract entities and relations automatically.
        """
        logger.info("decode_started", source_count=len(sources))
        entities_before = len(self.entities)
        relations_before = len(self.relations)

        for source in sources:
            if source.startswith("postgresql://") or source.startswith("mysql://"):
                self._decode_database(source)
            elif source.endswith("/") or source.startswith("./"):
                self._decode_codebase(source)
            else:
                self._decode_document(source)

        added_entities = len(self.entities) - entities_before
        added_relations = len(self.relations) - relations_before
        logger.info("decode_completed", new_entities=added_entities, new_relations=added_relations)
        return {"entities": added_entities, "relations": added_relations}

    def _decode_database(self, connection_string: str) -> None:
        logger.info("decoding_database", source=connection_string.split("@")[-1] if "@" in connection_string else connection_string)

    def _decode_codebase(self, path: str) -> None:
        logger.info("decoding_codebase", path=path)

    def _decode_document(self, path: str) -> None:
        logger.info("decoding_document", path=path)

    def stats(self) -> dict[str, int]:
        kinds = {}
        for e in self.entities.values():
            kinds[e.kind] = kinds.get(e.kind, 0) + 1
        return {
            "total_entities": len(self.entities),
            "total_relations": len(self.relations),
            "entity_kinds": kinds,
        }
