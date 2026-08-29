from __future__ import annotations

import json

from gn_as_code import Graph, dumps, from_dict, loads, to_dict
from gn_as_code.dump import fingerprint, to_mermaid
from gn_as_code.samples import build_column


def test_roundtrip_dict() -> None:
    graph = build_column()
    payload = graph.to_dict()
    restored = from_dict(payload)
    assert to_dict(restored) == payload


def test_dumps_is_stable() -> None:
    a = dumps(build_column().to_data())
    b = dumps(build_column().to_data())
    assert a == b
    json.loads(a)


def test_loads_roundtrip_text() -> None:
    text = build_column().dumps()
    assert dumps(loads(text)) == text


def test_fingerprint_ignores_layout() -> None:
    g = Graph("A")
    cube = g.mesh_cube(id="cube", location=(10, 20))
    g.output_geometry(cube)
    other = Graph("A")
    cube2 = other.mesh_cube(id="cube", location=(99, -4))
    other.output_geometry(cube2)
    assert fingerprint(g.to_data()) == fingerprint(other.to_data())
    assert fingerprint(g.to_data(), include_layout=True) != fingerprint(
        other.to_data(), include_layout=True
    )


def test_canonical_node_order() -> None:
    g = Graph("Order")
    b = g.mesh_grid(id="b")
    a = g.mesh_cube(id="a")
    g.output_geometry(g.join_geometry(a, b, id="join"))
    ids = [n["id"] for n in g.to_dict()["nodes"]]
    assert ids == sorted(ids)


def test_mermaid_contains_nodes_and_edges() -> None:
    text = to_mermaid(build_column().to_data())
    assert text.startswith("flowchart LR")
    assert "shaft" in text
    assert "-->" in text
