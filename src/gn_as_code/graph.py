"""Typed Geometry Node graph builder.

A ``Graph`` is both the authoring API and the in-memory IR. Call ``to_dict`` /
``dumps`` when you want the version-controlled artifact.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from gn_as_code.catalog import (
    CATALOG_BY_METHOD,
    GROUP_INPUT,
    GROUP_OUTPUT,
    NodeSpec,
    get_spec,
    values_equal,
)
from gn_as_code.ir import GraphData, InterfaceItem, Link, Node
from gn_as_code.types import GraphKind, JsonValue, SocketType, jsonify

InputValue = Any


def _snake_to_socket(name: str) -> str:
    specials = {
        "value_001": "Value_001",
        "value_002": "Value_002",
        "vector_001": "Vector_001",
        "vector_002": "Vector_002",
        "boolean_001": "Boolean_001",
        "mesh_1": "Mesh 1",
        "mesh_2": "Mesh 2",
        "from_min": "From Min",
        "from_max": "From Max",
        "to_min": "To Min",
        "to_max": "To Max",
        "size_x": "Size X",
        "size_y": "Size Y",
        "vertices_x": "Vertices X",
        "vertices_y": "Vertices Y",
        "vertices_z": "Vertices Z",
        "start_location": "Start Location",
        "offset_scale": "Offset Scale",
        "distance_min": "Distance Min",
        "density_max": "Density Max",
        "density_factor": "Density Factor",
        "pick_instance": "Pick Instance",
        "instance_index": "Instance Index",
        "realize_all": "Realize All",
        "profile_curve": "Profile Curve",
        "fill_caps": "Fill Caps",
        "shade_smooth": "Shade Smooth",
        "as_instance": "As Instance",
        "keep_boundaries": "Keep Boundaries",
        "dual_mesh": "Dual Mesh",
        "convex_hull": "Convex Hull",
        "bounding_box": "Bounding Box",
        "sample_position": "Sample Position",
        "local_space": "Local Space",
        "pivot_point": "Pivot Point",
        "radius_top": "Radius Top",
        "radius_bottom": "Radius Bottom",
        "side_segments": "Side Segments",
        "fill_segments": "Fill Segments",
        "minimum_vertices": "Minimum Vertices",
        "self_intersection": "Self Intersection",
        "hole_tolerant": "Hole Tolerant",
        "edge_crease": "Edge Crease",
        "vertex_crease": "Vertex Crease",
        "limit_radius": "Limit Radius",
    }
    if name in specials:
        return specials[name]
    return name.replace("_", " ").title()


@dataclass(frozen=True)
class SocketRef:
    """A named output (or group-input) socket that can be wired into another node."""

    node: str
    socket: str
    socket_type: SocketType | None = None

    def as_link_src(self) -> tuple[str, str]:
        return self.node, self.socket


@dataclass
class NodeHandle:
    """Handle to a node already in the graph. Attribute access yields output sockets."""

    graph: Graph
    id: str
    spec: NodeSpec | None = None

    def out(self, socket: str) -> SocketRef:
        spec = self.spec
        socket_type = None
        if spec is not None:
            found = spec.output_map().get(socket)
            if found is None:
                lowered = {s.identifier.lower(): s for s in spec.outputs}
                found = lowered.get(socket.lower())
            if found is not None:
                socket = found.identifier
                socket_type = found.socket_type
        return SocketRef(self.id, socket, socket_type)

    def __getitem__(self, socket: str | int) -> SocketRef:
        if isinstance(socket, int):
            if self.spec is None or socket >= len(self.spec.outputs):
                return SocketRef(self.id, str(socket))
            spec = self.spec.outputs[socket]
            return SocketRef(self.id, spec.identifier, spec.socket_type)
        return self.out(socket)

    def __getattr__(self, name: str) -> SocketRef:
        if name.startswith("_"):
            raise AttributeError(name)
        if self.spec is not None:
            ident = _snake_to_socket(name)
            outputs = self.spec.output_map()
            if ident in outputs:
                return self.out(ident)
            lowered = {key.lower(): key for key in outputs}
            if ident.lower() in lowered:
                return self.out(lowered[ident.lower()])
            if name.lower() == "geo" and "Geometry" in outputs:
                return self.out("Geometry")
            if name.lower() == "mesh" and "Mesh" in outputs:
                return self.out("Mesh")
        return self.out(_snake_to_socket(name))

    def as_socket(self) -> SocketRef:
        if self.spec is not None:
            primary = self.spec.primary_output()
            if primary is not None:
                return SocketRef(self.id, primary.identifier, primary.socket_type)
            if len(self.spec.outputs) == 1:
                only = self.spec.outputs[0]
                return SocketRef(self.id, only.identifier, only.socket_type)
        return SocketRef(self.id, "Geometry", SocketType.GEOMETRY)


class Graph:
    """Author a Geometry Node tree as data."""

    def __init__(
        self,
        name: str,
        *,
        kind: GraphKind | str = GraphKind.MODIFIER,
        blender: str = "4.2",
    ) -> None:
        self.name = name
        self.kind = GraphKind(kind)
        self.blender = blender
        self._inputs: list[InterfaceItem] = []
        self._outputs: list[InterfaceItem] = []
        self._nodes: dict[str, Node] = {}
        self._links: list[Link] = []
        self._used_ids: set[str] = set()
        self._input_node_id = "Group Input"
        self._output_node_id = "Group Output"
        self._ensure_io_nodes()

    # --- interface ---------------------------------------------------------

    def input(
        self,
        name: str,
        socket: SocketType | str,
        default: JsonValue = None,
        *,
        min: float | None = None,
        max: float | None = None,
        subtype: str | None = None,
        description: str = "",
    ) -> SocketRef:
        sock = socket if isinstance(socket, SocketType) else SocketType(socket)
        item = InterfaceItem(
            name=name,
            socket=sock,
            default=jsonify(default) if default is not None else None,
            min=min,
            max=max,
            subtype=subtype,
            description=description,
        )
        existing = next((i for i in self._inputs if i.name == name), None)
        if existing is not None:
            self._inputs[self._inputs.index(existing)] = item
        else:
            self._inputs.append(item)
        return SocketRef(self._input_node_id, name, sock)

    def input_geometry(self, name: str = "Geometry") -> SocketRef:
        return self.input(name, SocketType.GEOMETRY)

    def input_float(
        self,
        name: str,
        default: float = 0.0,
        *,
        min: float | None = None,
        max: float | None = None,
        subtype: str | None = None,
        description: str = "",
    ) -> SocketRef:
        return self.input(
            name,
            SocketType.FLOAT,
            default,
            min=min,
            max=max,
            subtype=subtype,
            description=description,
        )

    def input_int(
        self,
        name: str,
        default: int = 0,
        *,
        min: float | None = None,
        max: float | None = None,
        description: str = "",
    ) -> SocketRef:
        return self.input(name, SocketType.INT, default, min=min, max=max, description=description)

    def input_bool(self, name: str, default: bool = False, *, description: str = "") -> SocketRef:
        return self.input(name, SocketType.BOOLEAN, default, description=description)

    def input_vector(
        self,
        name: str,
        default: Sequence[float] = (0.0, 0.0, 0.0),
        *,
        description: str = "",
    ) -> SocketRef:
        return self.input(name, SocketType.VECTOR, tuple(default), description=description)

    def output(
        self,
        source: InputValue,
        name: str = "Geometry",
        socket: SocketType | str | None = None,
    ) -> SocketRef:
        sock = None if socket is None else (
            socket if isinstance(socket, SocketType) else SocketType(socket)
        )
        if isinstance(source, SocketRef) and sock is None:
            sock = source.socket_type
        if isinstance(source, NodeHandle) and sock is None:
            source = source.as_socket()
            sock = source.socket_type
        if sock is None:
            sock = SocketType.GEOMETRY
        item = InterfaceItem(name=name, socket=sock)
        existing = next((i for i in self._outputs if i.name == name), None)
        if existing is not None:
            self._outputs[self._outputs.index(existing)] = item
        else:
            self._outputs.append(item)
        self._connect(source, self._output_node_id, name)
        return SocketRef(self._output_node_id, name, sock)

    def output_geometry(self, source: InputValue, name: str = "Geometry") -> SocketRef:
        return self.output(source, name, SocketType.GEOMETRY)

    # --- generic node spawn ------------------------------------------------

    def node(
        self,
        bl_idname: str,
        *,
        id: str | None = None,
        label: str = "",
        location: Sequence[float] | None = None,
        hide: bool = False,
        mute: bool = False,
        parent: str | None = None,
        inputs: dict[str, InputValue] | None = None,
        properties: dict[str, Any] | None = None,
    ) -> NodeHandle:
        spec = get_spec(bl_idname)
        node_id = self._fresh_id(id or (spec.method if spec else bl_idname))
        recorded_inputs: dict[str, JsonValue] = {}
        for key, value in (inputs or {}).items():
            ident = self._resolve_input_ident(spec, key)
            if isinstance(value, (SocketRef, NodeHandle)):
                self._connect(value, node_id, ident)
                continue
            if spec is not None:
                sock = spec.input_map().get(ident)
                if sock is not None and sock.default is not None and values_equal(value, sock.default):
                    continue
            recorded_inputs[ident] = jsonify(value)
        recorded_props: dict[str, JsonValue] = {}
        for key, value in (properties or {}).items():
            if spec is not None:
                prop = next((p for p in spec.properties if p.name == key), None)
                if prop is not None and values_equal(value, prop.default):
                    continue
            recorded_props[key] = jsonify(value)
        loc = None if location is None else (float(location[0]), float(location[1]))
        self._nodes[node_id] = Node(
            id=node_id,
            type=bl_idname,
            label=label,
            location=loc,
            hide=hide,
            mute=mute,
            parent=parent,
            inputs=recorded_inputs,
            properties=recorded_props,
        )
        return NodeHandle(self, node_id, spec)

    def link(self, source: InputValue, target: NodeHandle | str, socket: str) -> None:
        node_id = target.id if isinstance(target, NodeHandle) else target
        self._connect(source, node_id, socket)

    # --- typed factories ---------------------------------------------------

    def mesh_cube(
        self,
        *,
        size: InputValue = (1.0, 1.0, 1.0),
        vertices_x: InputValue = 2,
        vertices_y: InputValue = 2,
        vertices_z: InputValue = 2,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshCube",
            id=id,
            inputs={"Size": size, "Vertices X": vertices_x, "Vertices Y": vertices_y, "Vertices Z": vertices_z},
            **node_kw,
        )

    def mesh_grid(
        self,
        *,
        size_x: InputValue = 1.0,
        size_y: InputValue = 1.0,
        vertices_x: InputValue = 3,
        vertices_y: InputValue = 3,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshGrid",
            id=id,
            inputs={"Size X": size_x, "Size Y": size_y, "Vertices X": vertices_x, "Vertices Y": vertices_y},
            **node_kw,
        )

    def mesh_uv_sphere(
        self,
        *,
        segments: InputValue = 32,
        rings: InputValue = 16,
        radius: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshUVSphere",
            id=id,
            inputs={"Segments": segments, "Rings": rings, "Radius": radius},
            **node_kw,
        )

    def mesh_ico_sphere(
        self,
        *,
        radius: InputValue = 1.0,
        subdivisions: InputValue = 1,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshIcoSphere",
            id=id,
            inputs={"Radius": radius, "Subdivisions": subdivisions},
            **node_kw,
        )

    def mesh_cylinder(
        self,
        *,
        vertices: InputValue = 32,
        radius: InputValue = 1.0,
        depth: InputValue = 2.0,
        fill_type: str = "NGON",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshCylinder",
            id=id,
            inputs={"Vertices": vertices, "Radius": radius, "Depth": depth},
            properties={"fill_type": fill_type},
            **node_kw,
        )

    def mesh_cone(
        self,
        *,
        vertices: InputValue = 32,
        radius_top: InputValue = 0.0,
        radius_bottom: InputValue = 1.0,
        depth: InputValue = 2.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshCone",
            id=id,
            inputs={
                "Vertices": vertices,
                "Radius Top": radius_top,
                "Radius Bottom": radius_bottom,
                "Depth": depth,
            },
            **node_kw,
        )

    def mesh_line(
        self,
        *,
        count: InputValue = 10,
        start_location: InputValue = (0.0, 0.0, 0.0),
        offset: InputValue = (0.0, 0.0, 1.0),
        mode: str = "OFFSET",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMeshLine",
            id=id,
            inputs={"Count": count, "Start Location": start_location, "Offset": offset},
            properties={"mode": mode},
            **node_kw,
        )

    def transform(
        self,
        geometry: InputValue,
        *,
        translation: InputValue = (0.0, 0.0, 0.0),
        rotation: InputValue = (0.0, 0.0, 0.0),
        scale: InputValue = (1.0, 1.0, 1.0),
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeTransform",
            id=id,
            inputs={
                "Geometry": geometry,
                "Translation": translation,
                "Rotation": rotation,
                "Scale": scale,
            },
            **node_kw,
        )

    def set_position(
        self,
        geometry: InputValue,
        *,
        offset: InputValue = (0.0, 0.0, 0.0),
        position: InputValue = None,
        selection: InputValue = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Geometry": geometry, "Offset": offset}
        if position is not None:
            inputs["Position"] = position
        if selection is not None:
            inputs["Selection"] = selection
        return self.node("GeometryNodeSetPosition", id=id, inputs=inputs, **node_kw)

    def join_geometry(self, *geometries: InputValue, id: str | None = None, **node_kw: Any) -> NodeHandle:
        handle = self.node("GeometryNodeJoinGeometry", id=id, **node_kw)
        for geo in geometries:
            self._connect(geo, handle.id, "Geometry")
        return handle

    def mesh_boolean(
        self,
        mesh_1: InputValue,
        mesh_2: InputValue | Iterable[InputValue],
        *,
        operation: str = "DIFFERENCE",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        handle = self.node(
            "GeometryNodeMeshBoolean",
            id=id,
            inputs={"Mesh 1": mesh_1},
            properties={"operation": operation},
            **node_kw,
        )
        others = mesh_2 if isinstance(mesh_2, (list, tuple)) else (mesh_2,)
        for geo in others:
            self._connect(geo, handle.id, "Mesh 2")
        return handle

    def subdivision_surface(
        self,
        mesh: InputValue,
        *,
        level: InputValue = 1,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeSubdivisionSurface",
            id=id,
            inputs={"Mesh": mesh, "Level": level},
            **node_kw,
        )

    def extrude_mesh(
        self,
        mesh: InputValue,
        *,
        offset_scale: InputValue = 1.0,
        offset: InputValue = None,
        individual: InputValue = True,
        mode: str = "FACES",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {
            "Mesh": mesh,
            "Offset Scale": offset_scale,
            "Individual": individual,
        }
        if offset is not None:
            inputs["Offset"] = offset
        return self.node(
            "GeometryNodeExtrudeMesh",
            id=id,
            inputs=inputs,
            properties={"mode": mode},
            **node_kw,
        )

    def distribute_points_on_faces(
        self,
        mesh: InputValue,
        *,
        density: InputValue = 10.0,
        seed: InputValue = 0,
        distribute_method: str = "RANDOM",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeDistributePointsOnFaces",
            id=id,
            inputs={"Mesh": mesh, "Density": density, "Seed": seed},
            properties={"distribute_method": distribute_method},
            **node_kw,
        )

    def instance_on_points(
        self,
        points: InputValue,
        instance: InputValue,
        *,
        rotation: InputValue = (0.0, 0.0, 0.0),
        scale: InputValue = (1.0, 1.0, 1.0),
        pick_instance: InputValue = False,
        instance_index: InputValue = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {
            "Points": points,
            "Instance": instance,
            "Rotation": rotation,
            "Scale": scale,
            "Pick Instance": pick_instance,
        }
        if instance_index is not None:
            inputs["Instance Index"] = instance_index
        return self.node("GeometryNodeInstanceOnPoints", id=id, inputs=inputs, **node_kw)

    def realize_instances(self, geometry: InputValue, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node(
            "GeometryNodeRealizeInstances",
            id=id,
            inputs={"Geometry": geometry},
            **node_kw,
        )

    def mesh_to_curve(self, mesh: InputValue, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("GeometryNodeMeshToCurve", id=id, inputs={"Mesh": mesh}, **node_kw)

    def curve_to_mesh(
        self,
        curve: InputValue,
        profile_curve: InputValue | None = None,
        *,
        fill_caps: InputValue = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Curve": curve, "Fill Caps": fill_caps}
        if profile_curve is not None:
            inputs["Profile Curve"] = profile_curve
        return self.node("GeometryNodeCurveToMesh", id=id, inputs=inputs, **node_kw)

    def curve_circle(
        self,
        *,
        resolution: InputValue = 32,
        radius: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeCurvePrimitiveCircle",
            id=id,
            inputs={"Resolution": resolution, "Radius": radius},
            **node_kw,
        )

    def set_material(
        self,
        geometry: InputValue,
        material: InputValue = None,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Geometry": geometry}
        if material is not None:
            inputs["Material"] = material
        return self.node("GeometryNodeSetMaterial", id=id, inputs=inputs, **node_kw)

    def set_shade_smooth(
        self,
        geometry: InputValue,
        shade_smooth: InputValue = True,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeSetShadeSmooth",
            id=id,
            inputs={"Geometry": geometry, "Shade Smooth": shade_smooth},
            **node_kw,
        )

    def bounding_box(self, geometry: InputValue, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("GeometryNodeBoundingBox", id=id, inputs={"Geometry": geometry}, **node_kw)

    def position(self, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("GeometryNodeInputPosition", id=id, **node_kw)

    def normal(self, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("GeometryNodeInputNormal", id=id, **node_kw)

    def index(self, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("GeometryNodeInputIndex", id=id, **node_kw)

    def noise_texture(
        self,
        *,
        scale: InputValue = 5.0,
        detail: InputValue = 2.0,
        roughness: InputValue = 0.5,
        lacunarity: InputValue = 2.0,
        distortion: InputValue = 0.0,
        vector: InputValue = None,
        noise_dimensions: str = "3D",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {
            "Scale": scale,
            "Detail": detail,
            "Roughness": roughness,
            "Lacunarity": lacunarity,
            "Distortion": distortion,
        }
        if vector is not None:
            inputs["Vector"] = vector
        return self.node(
            "ShaderNodeTexNoise",
            id=id,
            inputs=inputs,
            properties={"noise_dimensions": noise_dimensions},
            **node_kw,
        )

    def math(
        self,
        operation: str,
        value: InputValue = 0.5,
        value_001: InputValue = 0.5,
        value_002: InputValue | None = None,
        *,
        use_clamp: bool = False,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Value": value, "Value_001": value_001}
        if value_002 is not None:
            inputs["Value_002"] = value_002
        return self.node(
            "ShaderNodeMath",
            id=id,
            inputs=inputs,
            properties={"operation": operation, "use_clamp": use_clamp},
            **node_kw,
        )

    def vector_math(
        self,
        operation: str,
        vector: InputValue = (0.0, 0.0, 0.0),
        vector_001: InputValue | None = None,
        *,
        scale: InputValue | None = None,
        vector_002: InputValue | None = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Vector": vector}
        if vector_001 is not None:
            inputs["Vector_001"] = vector_001
        if vector_002 is not None:
            inputs["Vector_002"] = vector_002
        if scale is not None:
            inputs["Scale"] = scale
        return self.node(
            "ShaderNodeVectorMath",
            id=id,
            inputs=inputs,
            properties={"operation": operation},
            **node_kw,
        )

    def map_range(
        self,
        value: InputValue,
        *,
        from_min: InputValue = 0.0,
        from_max: InputValue = 1.0,
        to_min: InputValue = 0.0,
        to_max: InputValue = 1.0,
        clamp: bool = True,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeMapRange",
            id=id,
            inputs={
                "Value": value,
                "From Min": from_min,
                "From Max": from_max,
                "To Min": to_min,
                "To Max": to_max,
            },
            properties={"clamp": clamp},
            **node_kw,
        )

    def clamp(
        self,
        value: InputValue,
        *,
        min: InputValue = 0.0,
        max: InputValue = 1.0,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "ShaderNodeClamp",
            id=id,
            inputs={"Value": value, "Min": min, "Max": max},
            **node_kw,
        )

    def compare(
        self,
        operation: str,
        a: InputValue,
        b: InputValue,
        *,
        data_type: str = "FLOAT",
        epsilon: InputValue | None = None,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"A": a, "B": b}
        if epsilon is not None:
            inputs["Epsilon"] = epsilon
        return self.node(
            "FunctionNodeCompare",
            id=id,
            inputs=inputs,
            properties={"operation": operation, "data_type": data_type},
            **node_kw,
        )

    def separate_xyz(self, vector: InputValue, *, id: str | None = None, **node_kw: Any) -> NodeHandle:
        return self.node("ShaderNodeSeparateXYZ", id=id, inputs={"Vector": vector}, **node_kw)

    def combine_xyz(
        self,
        x: InputValue = 0.0,
        y: InputValue = 0.0,
        z: InputValue = 0.0,
        *,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node("ShaderNodeCombineXYZ", id=id, inputs={"X": x, "Y": y, "Z": z}, **node_kw)

    def switch(
        self,
        switch: InputValue,
        false: InputValue,
        true: InputValue,
        *,
        input_type: str = "GEOMETRY",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeSwitch",
            id=id,
            inputs={"Switch": switch, "False": false, "True": true},
            properties={"input_type": input_type},
            **node_kw,
        )

    def store_named_attribute(
        self,
        geometry: InputValue,
        name: InputValue,
        value: InputValue,
        *,
        data_type: str = "FLOAT",
        domain: str = "POINT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeStoreNamedAttribute",
            id=id,
            inputs={"Geometry": geometry, "Name": name, "Value": value},
            properties={"data_type": data_type, "domain": domain},
            **node_kw,
        )

    def named_attribute(
        self,
        name: InputValue,
        *,
        data_type: str = "FLOAT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeNamedAttribute",
            id=id,
            inputs={"Name": name},
            properties={"data_type": data_type},
            **node_kw,
        )

    def capture_attribute(
        self,
        geometry: InputValue,
        value: InputValue,
        *,
        data_type: str = "FLOAT_VECTOR",
        domain: str = "POINT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeCaptureAttribute",
            id=id,
            inputs={"Geometry": geometry, "Value": value},
            properties={"data_type": data_type, "domain": domain},
            **node_kw,
        )

    def random_value(
        self,
        *,
        min: InputValue = 0.0,
        max: InputValue = 1.0,
        seed: InputValue = 0,
        data_type: str = "FLOAT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "FunctionNodeRandomValue",
            id=id,
            inputs={"Min": min, "Max": max, "Seed": seed},
            properties={"data_type": data_type},
            **node_kw,
        )

    def object_info(
        self,
        obj: InputValue = None,
        *,
        as_instance: InputValue = False,
        transform_space: str = "ORIGINAL",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"As Instance": as_instance}
        if obj is not None:
            inputs["Object"] = obj
        return self.node(
            "GeometryNodeObjectInfo",
            id=id,
            inputs=inputs,
            properties={"transform_space": transform_space},
            **node_kw,
        )

    def align_rotation_to_vector(
        self,
        vector: InputValue,
        *,
        rotation: InputValue | None = None,
        factor: InputValue = 1.0,
        axis: str = "X",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        inputs: dict[str, InputValue] = {"Vector": vector, "Factor": factor}
        if rotation is not None:
            inputs["Rotation"] = rotation
        return self.node(
            "GeometryNodeAlignRotationToVector",
            id=id,
            inputs=inputs,
            properties={"axis": axis},
            **node_kw,
        )

    def merge_by_distance(
        self,
        geometry: InputValue,
        *,
        distance: InputValue = 0.001,
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeMergeByDistance",
            id=id,
            inputs={"Geometry": geometry, "Distance": distance},
            **node_kw,
        )

    def delete_geometry(
        self,
        geometry: InputValue,
        selection: InputValue,
        *,
        domain: str = "POINT",
        id: str | None = None,
        **node_kw: Any,
    ) -> NodeHandle:
        return self.node(
            "GeometryNodeDeleteGeometry",
            id=id,
            inputs={"Geometry": geometry, "Selection": selection},
            properties={"domain": domain},
            **node_kw,
        )

    def __getattr__(self, name: str) -> Any:
        spec = CATALOG_BY_METHOD.get(name)
        if spec is None:
            raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}")

        def factory(*args: Any, id: str | None = None, **kwargs: Any) -> NodeHandle:
            inputs: dict[str, InputValue] = {}
            properties: dict[str, Any] = {}
            positional = list(args)
            for sock in spec.inputs:
                if sock.identifier in kwargs:
                    inputs[sock.identifier] = kwargs.pop(sock.identifier)
                elif positional:
                    inputs[sock.identifier] = positional.pop(0)
            for prop in spec.properties:
                if prop.name in kwargs:
                    properties[prop.name] = kwargs.pop(prop.name)
            node_kw = kwargs
            return self.node(
                spec.bl_idname,
                id=id,
                inputs=inputs,
                properties=properties,
                **node_kw,
            )

        factory.__name__ = spec.method
        factory.__doc__ = f"Create a {spec.label} ({spec.bl_idname}) node."
        return factory

    # --- layout ------------------------------------------------------------

    def autolayout(self, *, x_step: float = 280.0, y_step: float = 140.0) -> None:
        """Assign stable left-to-right locations from topology. Existing locations win."""
        levels = self._levels()
        for level, ids in enumerate(levels):
            count = len(ids)
            for i, node_id in enumerate(sorted(ids)):
                node = self._nodes[node_id]
                if node.location is not None:
                    continue
                y = (count - 1) * y_step / 2.0 - i * y_step
                node.location = (level * x_step, y)

    # --- serialize ---------------------------------------------------------

    def to_data(self, *, autolayout: bool = True) -> GraphData:
        if autolayout:
            self.autolayout()
        if not any(item.name == "Geometry" for item in self._outputs):
            # Modifier graphs without an output are invalid; leave that to validate.
            pass
        return GraphData(
            name=self.name,
            kind=self.kind,
            blender=self.blender,
            interface_inputs=list(self._inputs),
            interface_outputs=list(self._outputs),
            nodes=list(self._nodes.values()),
            links=list(self._links),
        ).canonical()

    def to_dict(self, *, autolayout: bool = True) -> dict[str, Any]:
        from gn_as_code.dump import to_dict

        return to_dict(self.to_data(autolayout=autolayout))

    def dumps(self, *, autolayout: bool = True) -> str:
        from gn_as_code.dump import dumps

        return dumps(self.to_data(autolayout=autolayout))

    def to_mermaid(self) -> str:
        from gn_as_code.dump import to_mermaid

        return to_mermaid(self.to_data(autolayout=False))

    @classmethod
    def from_data(cls, data: GraphData) -> Graph:
        graph = cls(data.name, kind=data.kind, blender=data.blender)
        graph._inputs = list(data.interface_inputs)
        graph._outputs = list(data.interface_outputs)
        graph._nodes = {node.id: node for node in data.nodes}
        graph._links = list(data.links)
        graph._used_ids = set(graph._nodes)
        if "Group Input" in graph._nodes:
            graph._input_node_id = "Group Input"
        if "Group Output" in graph._nodes:
            graph._output_node_id = "Group Output"
        return graph

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Graph:
        return cls.from_data(GraphData.from_dict(data))

    # --- internals ---------------------------------------------------------

    def _ensure_io_nodes(self) -> None:
        if self._input_node_id not in self._nodes:
            self._nodes[self._input_node_id] = Node(
                id=self._input_node_id,
                type=GROUP_INPUT,
            )
            self._used_ids.add(self._input_node_id)
        if self._output_node_id not in self._nodes:
            self._nodes[self._output_node_id] = Node(
                id=self._output_node_id,
                type=GROUP_OUTPUT,
            )
            self._used_ids.add(self._output_node_id)

    def _fresh_id(self, base: str) -> str:
        candidate = base
        n = 1
        while candidate in self._used_ids:
            n += 1
            candidate = f"{base}_{n}"
        self._used_ids.add(candidate)
        return candidate

    def _resolve_input_ident(self, spec: NodeSpec | None, key: str) -> str:
        if spec is None:
            return key
        if key in spec.input_map():
            return key
        ident = _snake_to_socket(key)
        if ident in spec.input_map():
            return ident
        lowered = {s.identifier.lower(): s.identifier for s in spec.inputs}
        if key.lower() in lowered:
            return lowered[key.lower()]
        return key

    def _as_socket(self, value: InputValue) -> SocketRef:
        if isinstance(value, SocketRef):
            return value
        if isinstance(value, NodeHandle):
            return value.as_socket()
        raise TypeError(f"Expected a socket or node handle, got {type(value)!r}")

    def _connect(self, source: InputValue, to_node: str, to_socket: str) -> None:
        ref = self._as_socket(source)
        spec = get_spec(self._nodes[to_node].type) if to_node in self._nodes else None
        ident = self._resolve_input_ident(spec, to_socket)
        link = Link(ref.node, ref.socket, to_node, ident)
        if any(existing.key() == link.key() for existing in self._links):
            return
        self._links.append(link)

    def _levels(self) -> list[list[str]]:
        incoming: dict[str, set[str]] = {node_id: set() for node_id in self._nodes}
        outgoing: dict[str, set[str]] = {node_id: set() for node_id in self._nodes}
        for link in self._links:
            if link.from_node in incoming and link.to_node in incoming:
                incoming[link.to_node].add(link.from_node)
                outgoing[link.from_node].add(link.to_node)
        levels: list[list[str]] = []
        remaining = set(self._nodes)
        while remaining:
            ready = [n for n in remaining if incoming[n].isdisjoint(remaining)]
            if not ready:
                ready = sorted(remaining)
            levels.append(ready)
            remaining.difference_update(ready)
        return levels
