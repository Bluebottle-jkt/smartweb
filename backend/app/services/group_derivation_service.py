"""
Group derivation service using relationship graph analysis.

Uses Union-Find algorithm for connected components discovery with
controlled graph traversal respecting max_hops and thresholds.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from datetime import date, datetime
from decimal import Decimal
from collections import defaultdict, deque
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.db.models import (
    GroupDefinitionRuleSet, DerivedGroup, DerivedGroupMembership,
    Relationship, Taxpayer, EntityType, RelationshipType
)


class UnionFind:
    """Union-Find data structure for connected components."""

    def __init__(self):
        self.parent: Dict[int, int] = {}
        self.rank: Dict[int, int] = {}

    def find(self, x: int) -> int:
        """Find root with path compression."""
        if x not in self.parent:
            self.parent[x] = x
            self.rank[x] = 0
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int) -> None:
        """Union by rank."""
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return

        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1

    def get_components(self) -> Dict[int, List[int]]:
        """Get connected components grouped by root."""
        components = defaultdict(list)
        for node in self.parent:
            root = self.find(node)
            components[root].append(node)
        return dict(components)


class GroupDerivationService:
    """Service for deriving groups from relationship graph."""

    @staticmethod
    def get_active_rule_set(db: Session) -> Optional[GroupDefinitionRuleSet]:
        """Get the active rule set."""
        return db.query(GroupDefinitionRuleSet).filter(
            GroupDefinitionRuleSet.is_active == True
        ).first()

    @staticmethod
    def _get_qualified_relationships(
        db: Session,
        rule_set: GroupDefinitionRuleSet,
        as_of_date: Optional[date]
    ) -> List[Relationship]:
        """Get relationships that qualify based on rule set."""
        query = db.query(Relationship)

        # Filter by relationship types
        if rule_set.include_relationship_types:
            type_enums = [RelationshipType(t) for t in rule_set.include_relationship_types]
            query = query.filter(Relationship.relationship_type.in_(type_enums))

        # Filter by confidence
        query = query.filter(
            or_(
                Relationship.confidence == None,
                Relationship.confidence >= rule_set.min_confidence
            )
        )

        # Filter by effective date
        if as_of_date:
            query = query.filter(
                or_(
                    Relationship.effective_from == None,
                    Relationship.effective_from <= as_of_date
                ),
                or_(
                    Relationship.effective_to == None,
                    Relationship.effective_to >= as_of_date
                )
            )

        return query.all()

    @staticmethod
    def _build_taxpayer_edges(
        relationships: List[Relationship],
        rule_set: GroupDefinitionRuleSet,
        db: Session
    ) -> Dict[int, Set[Tuple[int, List[int]]]]:
        """
        Build taxpayer-to-taxpayer edges from relationships.
        Returns: {taxpayer_id: {(connected_taxpayer_id, [relationship_ids])}}
        """
        edges: Dict[int, Set[Tuple[int, List[int]]]] = defaultdict(set)

        direct_threshold = float(rule_set.direct_ownership_threshold_pct)
        control_as_affiliation = rule_set.control_as_affiliation

        for rel in relationships:
            # Direct taxpayer-to-taxpayer relationships
            if (rel.from_entity_type == EntityType.TAXPAYER and
                rel.to_entity_type == EntityType.TAXPAYER):

                from_id = rel.from_entity_id
                to_id = rel.to_entity_id

                # CONTROL always qualifies if configured
                if rel.relationship_type == RelationshipType.CONTROL and control_as_affiliation:
                    edges[from_id].add((to_id, [rel.id]))
                    edges[to_id].add((from_id, [rel.id]))  # Bidirectional

                # OWNERSHIP qualifies if above threshold
                elif rel.relationship_type == RelationshipType.OWNERSHIP:
                    if rel.pct and float(rel.pct) >= direct_threshold:
                        edges[from_id].add((to_id, [rel.id]))
                        edges[to_id].add((from_id, [rel.id]))  # Bidirectional

        # Handle BO-shared relationships if enabled
        if rule_set.bo_shared_any:
            GroupDerivationService._add_bo_shared_edges(
                relationships, edges, rule_set, db
            )

        return edges

    @staticmethod
    def _add_bo_shared_edges(
        relationships: List[Relationship],
        edges: Dict[int, Set[Tuple[int, List[int]]]],
        rule_set: GroupDefinitionRuleSet,
        db: Session
    ) -> None:
        """Add edges for taxpayers sharing BOs."""
        # Build BO->Taxpayer mapping
        bo_to_taxpayers: Dict[int, List[Tuple[int, List[int]]]] = defaultdict(list)

        for rel in relationships:
            if (rel.from_entity_type == EntityType.BENEFICIAL_OWNER and
                rel.to_entity_type == EntityType.TAXPAYER and
                rel.relationship_type == RelationshipType.OWNERSHIP):

                bo_id = rel.from_entity_id
                tp_id = rel.to_entity_id

                # Check bo_shared_min_pct if configured
                if rule_set.bo_shared_min_pct:
                    if not rel.pct or float(rel.pct) < float(rule_set.bo_shared_min_pct):
                        continue

                bo_to_taxpayers[bo_id].append((tp_id, [rel.id]))

        # Connect taxpayers sharing the same BO
        for bo_id, taxpayer_list in bo_to_taxpayers.items():
            if len(taxpayer_list) < 2:
                continue

            # Create edges between all pairs sharing this BO
            for i, (tp1, rel_ids1) in enumerate(taxpayer_list):
                for tp2, rel_ids2 in taxpayer_list[i + 1:]:
                    combined_rel_ids = list(set(rel_ids1 + rel_ids2))
                    edges[tp1].add((tp2, combined_rel_ids))
                    edges[tp2].add((tp1, combined_rel_ids))

    @staticmethod
    def _compute_connected_components(
        edges: Dict[int, Set[Tuple[int, List[int]]]],
        max_hops: int
    ) -> Tuple[Dict[int, List[int]], Dict[Tuple[int, int], List[List[int]]]]:
        """
        Compute connected components using BFS with max_hops constraint.
        Returns: (components, paths_evidence)
        """
        uf = UnionFind()
        paths_evidence: Dict[Tuple[int, int], List[List[int]]] = defaultdict(list)

        # BFS from each node to discover reachable nodes within max_hops
        all_nodes = set(edges.keys())
        for start in all_nodes:
            visited = {start}
            queue = deque([(start, 0, [])])  # (node, hops, path_rel_ids)

            while queue:
                current, hops, path = queue.popleft()

                if hops >= max_hops:
                    continue

                for neighbor, rel_ids in edges.get(current, set()):
                    if neighbor not in visited:
                        visited.add(neighbor)
                        new_path = path + rel_ids
                        queue.append((neighbor, hops + 1, new_path))

                        # Union components
                        uf.union(start, neighbor)

                        # Store path evidence
                        key = tuple(sorted([start, neighbor]))
                        paths_evidence[key].append(new_path)

        return uf.get_components(), paths_evidence

    @staticmethod
    def derive_groups(
        db: Session,
        rule_set_id: Optional[int] = None,
        as_of_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        Derive groups from relationship graph based on rule set.
        Returns summary of derivation.
        """
        start_time = datetime.utcnow()

        # Get rule set
        if rule_set_id:
            rule_set = db.query(GroupDefinitionRuleSet).filter(
                GroupDefinitionRuleSet.id == rule_set_id
            ).first()
            if not rule_set:
                raise ValueError(f"Rule set {rule_set_id} not found")
        else:
            rule_set = GroupDerivationService.get_active_rule_set(db)
            if not rule_set:
                raise ValueError("No active rule set found")

        # Delete previous derived groups for this rule_set + as_of_date
        existing = db.query(DerivedGroup).filter(
            DerivedGroup.rule_set_id == rule_set.id
        )
        if as_of_date:
            existing = existing.filter(DerivedGroup.as_of_date == as_of_date)
        else:
            existing = existing.filter(DerivedGroup.as_of_date == None)

        existing.delete(synchronize_session=False)

        # Get qualified relationships
        relationships = GroupDerivationService._get_qualified_relationships(
            db, rule_set, as_of_date
        )

        # Build taxpayer edges
        edges = GroupDerivationService._build_taxpayer_edges(
            relationships, rule_set, db
        )

        # Compute connected components
        components, paths_evidence = GroupDerivationService._compute_connected_components(
            edges, rule_set.max_hops
        )

        # Filter by min_members and persist
        groups_created = 0
        total_memberships = 0

        for root, members in components.items():
            if len(members) < rule_set.min_members:
                continue

            # Create derived group
            group_key = f"DRV-{rule_set.id}-{as_of_date or 'CURRENT'}-{root}"
            derived_group = DerivedGroup(
                rule_set_id=rule_set.id,
                group_key=group_key,
                as_of_date=as_of_date,
                summary={
                    "size": len(members),
                    "root_taxpayer_id": root,
                    "generated_with_rule": rule_set.name
                }
            )
            db.add(derived_group)
            db.flush()  # Get ID

            # Create memberships with evidence
            for member_id in members:
                # Compute strength score (heuristic: based on connectivity)
                strength = min(100, len(edges.get(member_id, set())) * 10)

                # Build evidence: paths to other members
                evidence_paths = []
                for other_member in members[:10]:  # Limit to 10 for evidence size
                    if other_member != member_id:
                        key = tuple(sorted([member_id, other_member]))
                        if key in paths_evidence and paths_evidence[key]:
                            evidence_paths.append({
                                "to_taxpayer_id": other_member,
                                "relationship_ids": paths_evidence[key][0]  # First path
                            })

                evidence = {
                    "paths": evidence_paths,
                    "total_connections": len(edges.get(member_id, set())),
                    "derivation_timestamp": datetime.utcnow().isoformat()
                }

                membership = DerivedGroupMembership(
                    derived_group_id=derived_group.id,
                    taxpayer_id=member_id,
                    strength_score=Decimal(str(strength)),
                    evidence=evidence
                )
                db.add(membership)
                total_memberships += 1

            groups_created += 1

        db.commit()

        end_time = datetime.utcnow()
        runtime_ms = int((end_time - start_time).total_seconds() * 1000)

        return {
            "number_of_groups": groups_created,
            "total_memberships": total_memberships,
            "runtime_ms": runtime_ms,
            "rule_set_id": rule_set.id,
            "rule_set_name": rule_set.name,
            "as_of_date": as_of_date.isoformat() if as_of_date else None
        }
