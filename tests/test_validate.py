from __future__ import annotations

from gn_as_code import Graph, GraphData, InterfaceItem, Link, Node, validate
from gn_as_code.types import SocketType


def test_valid_graph_has_no_errors() -> None:
    g = Graph("Ok")
    g.output_geometry(g.mesh_cube(id="cube"))
    assert validate(g.to_data()) == []


def test_unwired_output() -> None:
    g = Graph("Bad")
    g.mesh_cube(id="cube")
    g.output_geometry(g.mesh_cube(id="other"))
    data = g.to_data()
    # Drop the output link.
    data.links = [ln for ln in data.links if ln.to_node != "Group Output"]
    codes = {e.code for e in validate(data)}
    assert "unwired_output" in codes


def test_dangling_link() -> None:
    g = Graph("Bad")
    g.output_geometry(g.mesh_cube(id="cube"))
    data = g.to_data()
    data.links.append(Link("missing", "Mesh", "Group Output", "Geometry"))
    codes = {e.code for e in validate(data)}
    assert "dangling_link" in codes


def test_unknown_socket_on_catalog_node() -> None:
    data = GraphData(
        name="Bad",
        interface_outputs=[InterfaceItem("Geometry", SocketType.GEOMETRY)],
        nodes=[
            Node(id="Group Input", type="NodeGroupInput"),
            Node(id="Group Output", type="NodeGroupOutput"),
            Node(id="cube", type="GeometryNodeMeshCube"),
        ],
        links=[Link("cube", "Nope", "Group Output", "Geometry")],
    )
    codes = {e.code for e in validate(data)}
    assert "unknown_socket" in codes


def test_invalid_enum_property() -> None:
    g = Graph("Bad")
    g.output_geometry(g.math("NOT_A_REAL_OP", 1, 2, id="math"))
    codes = {e.code for e in validate(g.to_data())}
    assert "invalid_property" in codes
