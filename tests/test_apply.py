from __future__ import annotations

from gn_as_code.apply import apply, dump_from_bpy, to_apply_script, to_dump_script
from gn_as_code.samples import build_column, build_scatter
from tests.fake_bpy import FakeBpy


def _ids(tree) -> set[str]:
    return {node.name for node in tree.nodes}


def _link_keys(tree) -> set[tuple[str, str, str, str]]:
    keys = set()
    for link in tree.links:
        keys.add(
            (
                link.from_node.name,
                link.from_socket.identifier,
                link.to_node.name,
                link.to_socket.identifier,
            )
        )
    return keys


def test_apply_column_creates_nodes_and_links() -> None:
    bpy = FakeBpy()
    graph = build_column().to_data()
    tree = apply(graph, bpy=bpy, object_name="Column")
    assert tree.name == "Column"
    assert tree.is_modifier is True
    assert "shaft" in _ids(tree)
    assert "join" in _ids(tree)
    keys = _link_keys(tree)
    assert ("join", "Geometry", "Group Output", "Geometry") in keys
    assert ("shaft", "Mesh", "place_shaft", "Geometry") in keys
    obj = bpy.data.objects["Column"]
    assert obj.modifiers["GeometryNodes"].node_group is tree


def test_apply_then_dump_preserves_topology() -> None:
    bpy = FakeBpy()
    original = build_scatter().to_data()
    tree = apply(original, bpy=bpy)
    dumped = dump_from_bpy(tree)
    assert dumped["name"] == original.name
    assert dumped["format"] == "gn-as-code"
    orig_ids = {n.id for n in original.nodes}
    dump_ids = {n["id"] for n in dumped["nodes"]}
    assert orig_ids == dump_ids
    orig_links = {(ln.from_node, ln.from_socket, ln.to_node, ln.to_socket) for ln in original.links}
    dump_links = {(ln["from"][0], ln["from"][1], ln["to"][0], ln["to"][1]) for ln in dumped["links"]}
    assert orig_links == dump_links
    rebuilt = apply(dumped, bpy=FakeBpy())
    assert _link_keys(rebuilt) == _link_keys(tree)


def test_apply_script_is_executable_python() -> None:
    script = to_apply_script(build_column().to_data(), object_name="Column")
    compile(script, "<apply>", "exec")
    assert "apply_graph_dict" in script
    assert '"name": "Column"' in script
    dump_script = to_dump_script("Column")
    compile(dump_script, "<dump>", "exec")
    assert "dump_tree_by_name" in dump_script
