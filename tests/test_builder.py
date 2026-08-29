from __future__ import annotations

from gn_as_code import Graph, SocketType, validate
from gn_as_code.samples import build_column, build_noise_displace, build_scatter


def test_cube_to_output_wires_mesh() -> None:
    g = Graph("Cube")
    cube = g.mesh_cube(size=(1, 2, 3), id="cube")
    g.output_geometry(cube)
    data = g.to_data()
    assert data.name == "Cube"
    assert {n.id for n in data.nodes} >= {"cube", "Group Input", "Group Output"}
    links = {(ln.from_node, ln.from_socket, ln.to_node, ln.to_socket) for ln in data.links}
    assert ("cube", "Mesh", "Group Output", "Geometry") in links
    node = data.node_map()["cube"]
    assert node.inputs["Size"] == [1, 2, 3]
    assert validate(data) == []


def test_input_socket_is_group_input_ref() -> None:
    g = Graph("Sized Cube")
    size = g.input_vector("Size", (1, 1, 1))
    cube = g.mesh_cube(size=size, id="cube")
    g.output_geometry(cube.mesh)
    data = g.to_data()
    assert data.interface_inputs[0].name == "Size"
    assert data.interface_inputs[0].socket == SocketType.VECTOR
    link = next(ln for ln in data.links if ln.to_node == "cube")
    assert link.from_node == "Group Input"
    assert link.from_socket == "Size"


def test_join_geometry_multi_input() -> None:
    g = Graph("Join")
    a = g.mesh_cube(id="a")
    b = g.mesh_grid(id="b")
    joined = g.join_geometry(a, b, id="join")
    g.output_geometry(joined)
    data = g.to_data()
    to_join = [ln for ln in data.links if ln.to_node == "join"]
    assert len(to_join) == 2
    assert all(ln.to_socket == "Geometry" for ln in to_join)


def test_duplicate_ids_get_suffix() -> None:
    g = Graph("Dup")
    g.mesh_cube(id="cube")
    second = g.mesh_cube(id="cube")
    g.output_geometry(second)
    assert second.id == "cube_2"


def test_handle_attr_and_index() -> None:
    g = Graph("Attr")
    cube = g.mesh_cube(id="cube")
    assert cube.mesh.socket == "Mesh"
    assert cube["Mesh"].node == "cube"
    assert cube[0].socket == "Mesh"
    g.output_geometry(cube)


def test_samples_validate() -> None:
    for build in (build_column, build_noise_displace, build_scatter):
        errors = validate(build().to_data())
        assert errors == [], errors
