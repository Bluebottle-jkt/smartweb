"""
GraphRepository – BFS/DFS graph traversal queries.

Centralises all raw graph queries so graph intelligence services
don't touch the ORM directly.
"""
from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from datetime import date

from app.db.models import Relationship, Taxpayer, BeneficialOwner, Officer
from app.db.models.relationship import RelationshipType


# Performance guardrails
MAX_DEPTH = 5
MAX_NODES = 500
MAX_EDGES = 1500


class GraphRepository:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Taxpayer lookup
    # ------------------------------------------------------------------

    def get_taxpayer_by_npwp(self, npwp: str) -> Optional[Taxpayer]:
        import re
        groups = re.findall(r'\d+', npwp)
        if len(groups) >= 2:
            pattern = f"%{groups[0]}%{groups[-1]}%"
        elif len(groups) == 1:
            pattern = f"%{groups[0]}%"
        else:
            pattern = f"%{re.sub(r'[.-]', '', npwp)}%"
        return (
            self.db.query(Taxpayer)
            .filter(Taxpayer.npwp_masked.ilike(pattern))
            .first()
        )

    def get_taxpayer(self, taxpayer_id: int) -> Optional[Taxpayer]:
        return self.db.query(Taxpayer).filter(Taxpayer.id == taxpayer_id).first()

    # ------------------------------------------------------------------
    # BFS ego-network
    # ------------------------------------------------------------------

    def bfs_ego_network(
        self,
        root_entity_type: str,
        root_entity_id: int,
        year: int,
        depth: int = 2,
        max_nodes: int = MAX_NODES,
        edge_types: Optional[List[str]] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        BFS up to `depth` hops from the root node.
        Returns (nodes, edges) as plain dicts.
        """
        depth = min(depth, MAX_DEPTH)
        max_nodes = min(max_nodes, MAX_NODES)

        visited_nodes: Dict[str, Dict] = {}
        visited_edges: Set[str] = set()
        edge_list: List[Dict] = []

        queue = deque()
        root_nid = f"{root_entity_type}_{root_entity_id}"
        queue.append((root_entity_type, root_entity_id, 0))
        visited_nodes[root_nid] = {
            "id": root_nid,
            "entity_type": root_entity_type,
            "entity_id": root_entity_id,
            "layer": 0,
        }

        while queue and len(visited_nodes) < max_nodes:
            etype, eid, layer = queue.popleft()
            if layer >= depth:
                continue

            # Query relationships where this entity is source or target
            # Filter by year via effective_from / effective_to dates
            year_start = date(year, 1, 1)
            year_end = date(year, 12, 31)
            from sqlalchemy import or_, and_
            year_filter = and_(
                or_(Relationship.effective_from.is_(None), Relationship.effective_from <= year_end),
                or_(Relationship.effective_to.is_(None), Relationship.effective_to >= year_start),
            )
            rel_qry = self.db.query(Relationship).filter(year_filter)
            if edge_types:
                rel_qry = rel_qry.filter(
                    Relationship.relationship_type.in_(edge_types)
                )

            rels_as_src = rel_qry.filter(
                Relationship.from_entity_type == etype,
                Relationship.from_entity_id == eid,
            ).limit(MAX_EDGES).all()

            rels_as_tgt = rel_qry.filter(
                Relationship.to_entity_type == etype,
                Relationship.to_entity_id == eid,
            ).limit(MAX_EDGES).all()

            for rel in [*rels_as_src, *rels_as_tgt]:
                if rel.from_entity_type == etype and rel.from_entity_id == eid:
                    nb_type, nb_id = rel.to_entity_type, rel.to_entity_id
                else:
                    nb_type, nb_id = rel.from_entity_type, rel.from_entity_id

                nb_nid = f"{nb_type}_{nb_id}"
                edge_id = f"e_{rel.id}"

                if nb_nid not in visited_nodes and len(visited_nodes) < max_nodes:
                    visited_nodes[nb_nid] = {
                        "id": nb_nid,
                        "entity_type": nb_type,
                        "entity_id": nb_id,
                        "layer": layer + 1,
                    }
                    queue.append((nb_type, nb_id, layer + 1))

                if edge_id not in visited_edges:
                    visited_edges.add(edge_id)
                    edge_list.append({
                        "id": edge_id,
                        "source": f"{rel.from_entity_type}_{rel.from_entity_id}",
                        "target": f"{rel.to_entity_type}_{rel.to_entity_id}",
                        "relationship_type": rel.relationship_type,
                        "label": rel.relationship_type,
                        "layer": layer,
                    })
                    if len(edge_list) >= MAX_EDGES:
                        break

        return list(visited_nodes.values()), edge_list

    # ------------------------------------------------------------------
    # BFS shortest path
    # ------------------------------------------------------------------

    def bfs_shortest_path(
        self,
        src_type: str,
        src_id: int,
        tgt_type: str,
        tgt_id: int,
        year: int,
        max_depth: int = MAX_DEPTH,
    ) -> Optional[List[str]]:
        """Returns node ID list of shortest path or None."""
        if src_type == tgt_type and src_id == tgt_id:
            return [f"{src_type}_{src_id}"]

        visited = {f"{src_type}_{src_id}": None}
        queue = deque([(src_type, src_id, 0)])

        while queue:
            etype, eid, depth = queue.popleft()
            if depth >= max_depth:
                continue

            sp_year_start = date(year, 1, 1)
            sp_year_end = date(year, 12, 31)
            from sqlalchemy import or_ as _or_, and_ as _and_
            sp_year_filter = _and_(
                _or_(Relationship.effective_from.is_(None), Relationship.effective_from <= sp_year_end),
                _or_(Relationship.effective_to.is_(None), Relationship.effective_to >= sp_year_start),
            )
            rels = (
                self.db.query(Relationship)
                .filter(
                    sp_year_filter,
                    (
                        (Relationship.from_entity_type == etype) &
                        (Relationship.from_entity_id == eid)
                    ) | (
                        (Relationship.to_entity_type == etype) &
                        (Relationship.to_entity_id == eid)
                    )
                )
                .limit(200)
                .all()
            )

            for rel in rels:
                if rel.from_entity_type == etype and rel.from_entity_id == eid:
                    nb_type, nb_id = rel.to_entity_type, rel.to_entity_id
                else:
                    nb_type, nb_id = rel.from_entity_type, rel.from_entity_id

                nb_nid = f"{nb_type}_{nb_id}"
                cur_nid = f"{etype}_{eid}"

                if nb_nid not in visited:
                    visited[nb_nid] = cur_nid
                    if nb_type == tgt_type and nb_id == tgt_id:
                        # Reconstruct path
                        path = []
                        node = nb_nid
                        while node is not None:
                            path.append(node)
                            node = visited[node]
                        path.reverse()
                        return path
                    queue.append((nb_type, nb_id, depth + 1))

        return None
