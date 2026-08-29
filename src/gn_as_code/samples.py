"""Example graphs shipped with the library.

These are the golden fixtures: Python is how you author, JSON is what git diffs.
"""

from __future__ import annotations

from gn_as_code.graph import Graph


def build_column() -> Graph:
    """Parametric column: plinth + shaft, both driven by Width / Height."""
    g = Graph("Column")
    height = g.input_float("Height", 2.0, min=0.1, max=20.0)
    width = g.input_float("Width", 0.4, min=0.05, max=5.0)
    plinth = g.input_float("Plinth", 0.15, min=0.0, max=2.0)

    size = g.combine_xyz(width, width, height, id="column_size")
    shaft = g.mesh_cube(size=size.vector, id="shaft")
    half = g.math("MULTIPLY", height, 0.5, id="half_height")
    lift = g.combine_xyz(0.0, 0.0, half.value, id="shaft_lift")
    shaft_xf = g.transform(shaft.mesh, translation=lift.vector, id="place_shaft")

    pad = g.math("ADD", width, 0.1, id="plinth_pad")
    plinth_size = g.combine_xyz(pad.value, pad.value, plinth, id="plinth_size")
    base = g.mesh_cube(size=plinth_size.vector, id="plinth")
    half_plinth = g.math("MULTIPLY", plinth, 0.5, id="half_plinth")
    base_lift = g.combine_xyz(0.0, 0.0, half_plinth.value, id="plinth_lift")
    base_xf = g.transform(base.mesh, translation=base_lift.vector, id="place_plinth")

    joined = g.join_geometry(base_xf.geometry, shaft_xf.geometry, id="join")
    g.output_geometry(joined.geometry)
    return g


def build_noise_displace() -> Graph:
    """UV sphere displaced along normals by a noise texture."""
    g = Graph("Noise Displace")
    radius = g.input_float("Radius", 1.0, min=0.1, max=10.0)
    strength = g.input_float("Strength", 0.15, min=0.0, max=2.0)
    scale = g.input_float("Scale", 4.0, min=0.01, max=50.0)

    sphere = g.mesh_uv_sphere(radius=radius, segments=48, rings=24, id="sphere")
    noise = g.noise_texture(scale=scale, detail=4.0, id="noise")
    fac = g.math("MULTIPLY", noise.fac, strength, id="amp")
    offset = g.vector_math("SCALE", g.normal().normal, scale=fac.value, id="offset")
    displaced = g.set_position(sphere.mesh, offset=offset.vector, id="displace")
    g.output_geometry(displaced.geometry)
    return g


def build_scatter() -> Graph:
    """Distribute ico-spheres across an input mesh."""
    g = Graph("Scatter On Mesh")
    mesh_in = g.input_geometry("Geometry")
    density = g.input_float("Density", 25.0, min=0.0, max=500.0)
    radius = g.input_float("Instance Radius", 0.05, min=0.001, max=1.0)
    seed = g.input_int("Seed", 0)

    points = g.distribute_points_on_faces(mesh_in, density=density, seed=seed, id="points")
    instance = g.mesh_ico_sphere(radius=radius, subdivisions=1, id="pebble")
    rotation = g.align_rotation_to_vector(points.normal, axis="Z", id="align")
    scattered = g.instance_on_points(
        points.points,
        instance.mesh,
        rotation=rotation.rotation,
        id="instances",
    )
    g.output_geometry(scattered.instances)
    return g


SAMPLES = {
    "column": build_column,
    "noise_displace": build_noise_displace,
    "scatter": build_scatter,
}
