from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user
from app.db.models import EntityType, Relationship, RelationshipType, Taxpayer, UserAccount, UserRole
from app.main import app


client = TestClient(app)


def _override_user(role: UserRole):
    def _override():
        return UserAccount(id=1, username="test", role=role, password_hash="x")
    return _override


def test_network_graph_depth_layers(db, override_get_db):
    app.dependency_overrides[get_current_user] = _override_user(UserRole.ADMIN)

    tp_nodes = []
    for idx in range(6):
        tp = Taxpayer(
            npwp_masked=f"0{idx}.***.***.1",
            name=f"TP{idx}",
            entity_type="PT",
            status="Aktif"
        )
        db.add(tp)
        tp_nodes.append(tp)
    db.commit()

    for idx in range(5):
        rel = Relationship(
            from_entity_type=EntityType.TAXPAYER,
            from_entity_id=tp_nodes[idx].id,
            to_entity_type=EntityType.TAXPAYER,
            to_entity_id=tp_nodes[idx + 1].id,
            relationship_type=RelationshipType.OWNERSHIP,
            effective_from=date(2022, 1, 1)
        )
        db.add(rel)
    db.commit()

    response = client.get(
        "/network/graph",
        params={
            "root_type": "TAXPAYER",
            "root_id": tp_nodes[0].id,
            "year": 2023,
            "depth": 5,
            "max_nodes": 100
        }
    )

    assert response.status_code == 200
    payload = response.json()
    layers = [node["layer"] for node in payload["nodes"]]
    assert max(layers) <= 5
    assert 5 in layers
    app.dependency_overrides.pop(get_current_user, None)


def test_network_graph_max_nodes_enforced(db, override_get_db):
    app.dependency_overrides[get_current_user] = _override_user(UserRole.VIEWER)

    tp = Taxpayer(
        npwp_masked="01.***.***.1",
        name="TP1",
        entity_type="PT",
        status="Aktif"
    )
    db.add(tp)
    db.commit()

    response = client.get(
        "/network/graph",
        params={
            "root_type": "TAXPAYER",
            "root_id": tp.id,
            "year": 2023,
            "depth": 2,
            "max_nodes": 1000
        }
    )

    assert response.status_code == 400
    app.dependency_overrides.pop(get_current_user, None)
