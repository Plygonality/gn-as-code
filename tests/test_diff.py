from __future__ import annotations

from gn_as_code import Graph, diff_graphs, format_diff
from gn_as_code.samples import build_column


def test_identical_graphs_empty_diff() -> None:
    a = build_column().to_data()
    b = build_column().to_data()
    diff = diff_graphs(a, b)
    assert diff.is_empty()
    assert format_diff(diff) == "No differences.\n"


def test_added_and_removed_nodes() -> None:
    old = Graph("G")
    old.output_geometry(old.mesh_cube(id="cube"))
    new = Graph("G")
    new.output_geometry(new.mesh_grid(id="grid"))
    diff = diff_graphs(old.to_data(), new.to_data())
    assert [n["id"] for n in diff.nodes_added] == ["grid"]
    assert [n["id"] for n in diff.nodes_removed] == ["cube"]
    assert any("cube.Mesh" in format_diff(diff) for _ in [0])


def test_changed_input_and_link() -> None:
    old = Graph("G")
    old.output_geometry(old.mesh_cube(size=(2, 3, 4), id="cube"))
    new = Graph("G")
    height = new.input_float("Height", 2.0)
    size = new.combine_xyz(1.0, 1.0, height, id="size")
    new.output_geometry(new.mesh_cube(size=size.vector, id="cube"))
    diff = diff_graphs(old.to_data(), new.to_data())
    assert any(n["id"] == "size" for n in diff.nodes_added)
    assert diff.interface_inputs is not None
    assert diff.links_added
    changed_ids = [c.id for c in diff.nodes_changed]
    assert "cube" in changed_ids


def test_layout_ignored_by_default() -> None:
    a = Graph("G")
    a.output_geometry(a.mesh_cube(id="cube", location=(0, 0)))
    b = Graph("G")
    b.output_geometry(b.mesh_cube(id="cube", location=(100, 50)))
    assert diff_graphs(a.to_data(autolayout=False), b.to_data(autolayout=False)).is_empty()
    diff = diff_graphs(
        a.to_data(autolayout=False),
        b.to_data(autolayout=False),
        include_layout=True,
    )
    assert not diff.is_empty()
    assert any(c.id == "cube" for c in diff.nodes_changed)
