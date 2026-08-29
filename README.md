# gn-as-code

Geometry Node trees as data. Git is the source of truth. The `.blend` is a cache.

Build graphs in Python. Dump them to JSON. Diff them like code.
[Plygon-mcp](https://github.com/Plygonality/Plygon-mcp) applies a graph and screenshots the viewport.

This is a library you import, not another `execute_python` wrapper.

```python
from pathlib import Path

from gn_as_code import Graph

g = Graph("Noise Displace")
radius = g.input_float("Radius", 1.0)
strength = g.input_float("Strength", 0.15)

sphere = g.mesh_uv_sphere(radius=radius, segments=48, rings=24)
noise = g.noise_texture(scale=4.0, detail=4.0)
offset = g.vector_math("SCALE", g.normal().normal, scale=g.math("MULTIPLY", noise.fac, strength).value)
g.output_geometry(g.set_position(sphere.mesh, offset=offset.vector))

Path("graphs/noise_displace.json").write_text(g.dumps())
```

## Why this repo exists

A Geometry Node tree in a `.blend` is a binary blob. You cannot review it, diff it, or let an agent iterate on it without opening Blender.

| Role | Job |
|---|---|
| **This library** | Typed builders, canonical JSON, structural diffs, golden tests |
| **Plygon-mcp** | Apply the JSON in a live Blender session and check the viewport |
| **The `.blend`** | Working cache, never the source of truth |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. No Blender required to build, dump, or diff.

## Graph JSON

Dumps are stable: nodes sorted by id, links sorted, defaults omitted, locations rounded.

```json
{
  "format": "gn-as-code",
  "version": 1,
  "name": "Column",
  "kind": "MODIFIER",
  "blender": "4.2",
  "interface": {
    "inputs": [{"name": "Height", "socket": "FLOAT", "default": 2.0}],
    "outputs": [{"name": "Geometry", "socket": "GEOMETRY"}]
  },
  "nodes": [
    {"id": "Group Input", "type": "NodeGroupInput"},
    {"id": "Group Output", "type": "NodeGroupOutput"},
    {"id": "shaft", "type": "GeometryNodeMeshCube"}
  ],
  "links": [
    {"from": ["shaft", "Mesh"], "to": ["Group Output", "Geometry"]}
  ]
}
```

`id` is the stable name. Rename nodes in the builder, not in Blender, so diffs stay readable.

## Diff

```python
from gn_as_code import diff_graphs, format_diff, loads

diff = diff_graphs(loads(old_json), loads(new_json))
print(format_diff(diff))
```

Locations are ignored unless you pass `include_layout=True`.

```bash
gn-as-code diff old.json new.json
gn-as-code validate graph.json
gn-as-code mermaid graph.json
```

## Apply in Blender (via Plygon-mcp)

The agent authors a graph here, then asks Plygon-mcp to run a self-contained bpy script. Blender does not need this package installed.

```python
from gn_as_code.apply import to_apply_script
from gn_as_code.samples import build_column

script = to_apply_script(build_column().to_data(), object_name="Column")
# Plygon-mcp: execute_blender_code(script) → get_viewport_screenshot()
```

Dump a live tree the other way:

```python
from gn_as_code.apply import to_dump_script

script = to_dump_script("Column")
```

If you are already inside Blender:

```python
from gn_as_code.apply import apply, dump_from_bpy
apply(graph.to_data(), object_name="Column")
```

## Typed builders

Common Geometry Nodes are methods on `Graph` (`mesh_cube`, `distribute_points_on_faces`, `instance_on_points`, `math`, `noise_texture`, …). Pass a socket or a node handle to wire a link; pass a literal to set a default.

Anything not wrapped is still valid:

```python
g.node("GeometryNodePointsToVolume", id="volume", inputs={"Points": points, "Radius": 0.1})
```

Unknown `bl_idname`s are allowed. The catalog is how builders name sockets and skip defaults without bpy.

## Tests

```bash
pytest -q
UPDATE_GOLDENS=1 pytest tests/test_golden.py   # rewrite fixtures after an intentional dump change
```

Goldens live in `tests/goldens/`. If a builder change is intentional, update them. If it is not, the test failed for a reason.

## Layout

```
src/gn_as_code/     library
examples/           sample graphs as Python
tests/goldens/      canonical JSON fixtures
```
