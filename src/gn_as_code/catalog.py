"""Catalog of common Geometry Nodes (Blender 4.2+).

Unknown nodes still work via ``Graph.node`` — the catalog exists so builders
can name sockets, skip defaults, and validate links without bpy.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gn_as_code.types import SocketType

ST = SocketType

GROUP_INPUT = "NodeGroupInput"
GROUP_OUTPUT = "NodeGroupOutput"


@dataclass(frozen=True)
class SocketSpec:
    identifier: str
    socket_type: SocketType
    default: Any = None
    multi: bool = False
    optional: bool = False


@dataclass(frozen=True)
class PropertySpec:
    name: str
    default: Any = None
    items: tuple[str, ...] = ()


@dataclass(frozen=True)
class NodeSpec:
    bl_idname: str
    method: str
    label: str
    inputs: tuple[SocketSpec, ...] = ()
    outputs: tuple[SocketSpec, ...] = ()
    properties: tuple[PropertySpec, ...] = ()

    def input_map(self) -> dict[str, SocketSpec]:
        return {s.identifier: s for s in self.inputs}

    def output_map(self) -> dict[str, SocketSpec]:
        return {s.identifier: s for s in self.outputs}

    def primary_output(self) -> SocketSpec | None:
        if not self.outputs:
            return None
        for sock in self.outputs:
            if sock.socket_type == SocketType.GEOMETRY:
                return sock
        return self.outputs[0]


def _s(
    identifier: str,
    socket_type: SocketType,
    default: Any = None,
    *,
    multi: bool = False,
    optional: bool = False,
) -> SocketSpec:
    return SocketSpec(identifier, socket_type, default, multi=multi, optional=optional)


def _p(name: str, default: Any = None, *items: str) -> PropertySpec:
    return PropertySpec(name, default, items)


_SPECS: tuple[NodeSpec, ...] = (
    NodeSpec(
        GROUP_INPUT,
        "group_input",
        "Group Input",
        outputs=(),
    ),
    NodeSpec(
        GROUP_OUTPUT,
        "group_output",
        "Group Output",
        inputs=(),
    ),
    NodeSpec(
        "GeometryNodeMeshCube",
        "mesh_cube",
        "Cube",
        inputs=(
            _s("Size", ST.VECTOR, (1.0, 1.0, 1.0)),
            _s("Vertices X", ST.INT, 2),
            _s("Vertices Y", ST.INT, 2),
            _s("Vertices Z", ST.INT, 2),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshGrid",
        "mesh_grid",
        "Grid",
        inputs=(
            _s("Size X", ST.FLOAT, 1.0),
            _s("Size Y", ST.FLOAT, 1.0),
            _s("Vertices X", ST.INT, 3),
            _s("Vertices Y", ST.INT, 3),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshUVSphere",
        "mesh_uv_sphere",
        "UV Sphere",
        inputs=(
            _s("Segments", ST.INT, 32),
            _s("Rings", ST.INT, 16),
            _s("Radius", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshIcoSphere",
        "mesh_ico_sphere",
        "Ico Sphere",
        inputs=(
            _s("Radius", ST.FLOAT, 1.0),
            _s("Subdivisions", ST.INT, 1),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshCylinder",
        "mesh_cylinder",
        "Cylinder",
        inputs=(
            _s("Vertices", ST.INT, 32),
            _s("Side Segments", ST.INT, 1),
            _s("Fill Segments", ST.INT, 1),
            _s("Radius", ST.FLOAT, 1.0),
            _s("Depth", ST.FLOAT, 2.0),
        ),
        outputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Top", ST.BOOLEAN),
            _s("Side", ST.BOOLEAN),
            _s("Bottom", ST.BOOLEAN),
        ),
        properties=(_p("fill_type", "NGON", "NONE", "NGON", "TRIANGLE"),),
    ),
    NodeSpec(
        "GeometryNodeMeshCone",
        "mesh_cone",
        "Cone",
        inputs=(
            _s("Vertices", ST.INT, 32),
            _s("Side Segments", ST.INT, 1),
            _s("Fill Segments", ST.INT, 1),
            _s("Radius Top", ST.FLOAT, 0.0),
            _s("Radius Bottom", ST.FLOAT, 1.0),
            _s("Depth", ST.FLOAT, 2.0),
        ),
        outputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Top", ST.BOOLEAN),
            _s("Bottom", ST.BOOLEAN),
            _s("Side", ST.BOOLEAN),
        ),
        properties=(_p("fill_type", "NGON", "NONE", "NGON", "TRIANGLE"),),
    ),
    NodeSpec(
        "GeometryNodeMeshLine",
        "mesh_line",
        "Mesh Line",
        inputs=(
            _s("Count", ST.INT, 10),
            _s("Resolution", ST.FLOAT, 1.0, optional=True),
            _s("Start Location", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Offset", ST.VECTOR, (0.0, 0.0, 1.0)),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
        properties=(_p("mode", "OFFSET", "OFFSET", "END_POINTS"),),
    ),
    NodeSpec(
        "GeometryNodeMeshCircle",
        "mesh_circle",
        "Mesh Circle",
        inputs=(
            _s("Vertices", ST.INT, 32),
            _s("Radius", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
        properties=(_p("fill_type", "NONE", "NONE", "NGON", "TRIANGLE"),),
    ),
    NodeSpec(
        "GeometryNodeTransform",
        "transform",
        "Transform Geometry",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Translation", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Rotation", ST.ROTATION, (0.0, 0.0, 0.0)),
            _s("Scale", ST.VECTOR, (1.0, 1.0, 1.0)),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
        properties=(_p("mode", "COMPONENTS", "COMPONENTS", "MATRIX"),),
    ),
    NodeSpec(
        "GeometryNodeSetPosition",
        "set_position",
        "Set Position",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Position", ST.VECTOR, optional=True),
            _s("Offset", ST.VECTOR, (0.0, 0.0, 0.0)),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeJoinGeometry",
        "join_geometry",
        "Join Geometry",
        inputs=(_s("Geometry", ST.GEOMETRY, multi=True),),
        outputs=(_s("Geometry", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshBoolean",
        "mesh_boolean",
        "Mesh Boolean",
        inputs=(
            _s("Mesh 1", ST.GEOMETRY),
            _s("Mesh 2", ST.GEOMETRY, multi=True),
            _s("Self Intersection", ST.BOOLEAN, False, optional=True),
            _s("Hole Tolerant", ST.BOOLEAN, False, optional=True),
        ),
        outputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Intersecting Edges", ST.BOOLEAN),
        ),
        properties=(
            _p("operation", "DIFFERENCE", "INTERSECT", "UNION", "DIFFERENCE"),
            _p("solver", "FLOAT", "EXACT", "FLOAT"),
        ),
    ),
    NodeSpec(
        "GeometryNodeSubdivisionSurface",
        "subdivision_surface",
        "Subdivision Surface",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Level", ST.INT, 1),
            _s("Edge Crease", ST.FLOAT, 0.0, optional=True),
            _s("Vertex Crease", ST.FLOAT, 0.0, optional=True),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeSubdivideMesh",
        "subdivide_mesh",
        "Subdivide Mesh",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Level", ST.INT, 1),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeExtrudeMesh",
        "extrude_mesh",
        "Extrude Mesh",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Offset", ST.VECTOR, optional=True),
            _s("Offset Scale", ST.FLOAT, 1.0),
            _s("Individual", ST.BOOLEAN, True),
        ),
        outputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Top", ST.BOOLEAN),
            _s("Side", ST.BOOLEAN),
        ),
        properties=(_p("mode", "FACES", "VERTICES", "EDGES", "FACES"),),
    ),
    NodeSpec(
        "GeometryNodeMergeByDistance",
        "merge_by_distance",
        "Merge by Distance",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Distance", ST.FLOAT, 0.001),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
        properties=(_p("mode", "ALL", "ALL", "CONNECTED"),),
    ),
    NodeSpec(
        "GeometryNodeDeleteGeometry",
        "delete_geometry",
        "Delete Geometry",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
        properties=(
            _p("domain", "POINT", "POINT", "EDGE", "FACE", "CURVE", "INSTANCE"),
            _p("mode", "ALL", "ALL", "EDGE_FACE", "ONLY_FACE"),
        ),
    ),
    NodeSpec(
        "GeometryNodeSeparateGeometry",
        "separate_geometry",
        "Separate Geometry",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True),
        ),
        outputs=(
            _s("Selection", ST.GEOMETRY),
            _s("Inverted", ST.GEOMETRY),
        ),
        properties=(_p("domain", "POINT", "POINT", "EDGE", "FACE", "CURVE", "INSTANCE"),),
    ),
    NodeSpec(
        "GeometryNodeDistributePointsOnFaces",
        "distribute_points_on_faces",
        "Distribute Points on Faces",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Distance Min", ST.FLOAT, 0.0, optional=True),
            _s("Density Max", ST.FLOAT, 10.0, optional=True),
            _s("Density Factor", ST.FLOAT, 1.0, optional=True),
            _s("Density", ST.FLOAT, 10.0),
            _s("Seed", ST.INT, 0),
        ),
        outputs=(
            _s("Points", ST.GEOMETRY),
            _s("Normal", ST.VECTOR),
            _s("Rotation", ST.ROTATION),
        ),
        properties=(_p("distribute_method", "RANDOM", "RANDOM", "POISSON"),),
    ),
    NodeSpec(
        "GeometryNodeInstanceOnPoints",
        "instance_on_points",
        "Instance on Points",
        inputs=(
            _s("Points", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Instance", ST.GEOMETRY),
            _s("Pick Instance", ST.BOOLEAN, False),
            _s("Instance Index", ST.INT, optional=True),
            _s("Rotation", ST.ROTATION, (0.0, 0.0, 0.0)),
            _s("Scale", ST.VECTOR, (1.0, 1.0, 1.0)),
        ),
        outputs=(_s("Instances", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeRealizeInstances",
        "realize_instances",
        "Realize Instances",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Realize All", ST.BOOLEAN, True, optional=True),
            _s("Depth", ST.INT, 0, optional=True),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshToCurve",
        "mesh_to_curve",
        "Mesh to Curve",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
        ),
        outputs=(_s("Curve", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeCurveToMesh",
        "curve_to_mesh",
        "Curve to Mesh",
        inputs=(
            _s("Curve", ST.GEOMETRY),
            _s("Profile Curve", ST.GEOMETRY, optional=True),
            _s("Fill Caps", ST.BOOLEAN, False),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeResampleCurve",
        "resample_curve",
        "Resample Curve",
        inputs=(
            _s("Curve", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Count", ST.INT, 10),
            _s("Length", ST.FLOAT, 0.1, optional=True),
        ),
        outputs=(_s("Curve", ST.GEOMETRY),),
        properties=(_p("mode", "COUNT", "EVALUATED", "COUNT", "LENGTH"),),
    ),
    NodeSpec(
        "GeometryNodeSetMaterial",
        "set_material",
        "Set Material",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Material", ST.MATERIAL, optional=True),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeSetShadeSmooth",
        "set_shade_smooth",
        "Set Shade Smooth",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Shade Smooth", ST.BOOLEAN, True),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
        properties=(_p("domain", "FACE", "POINT", "EDGE", "FACE"),),
    ),
    NodeSpec(
        "GeometryNodeBoundingBox",
        "bounding_box",
        "Bounding Box",
        inputs=(_s("Geometry", ST.GEOMETRY),),
        outputs=(
            _s("Bounding Box", ST.GEOMETRY),
            _s("Min", ST.VECTOR),
            _s("Max", ST.VECTOR),
        ),
    ),
    NodeSpec(
        "GeometryNodeConvexHull",
        "convex_hull",
        "Convex Hull",
        inputs=(_s("Geometry", ST.GEOMETRY),),
        outputs=(_s("Convex Hull", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeObjectInfo",
        "object_info",
        "Object Info",
        inputs=(
            _s("Object", ST.OBJECT, optional=True),
            _s("As Instance", ST.BOOLEAN, False),
        ),
        outputs=(
            _s("Transform", ST.MATRIX),
            _s("Location", ST.VECTOR),
            _s("Rotation", ST.ROTATION),
            _s("Scale", ST.VECTOR),
            _s("Geometry", ST.GEOMETRY),
        ),
        properties=(_p("transform_space", "ORIGINAL", "ORIGINAL", "RELATIVE"),),
    ),
    NodeSpec(
        "GeometryNodeInputPosition",
        "position",
        "Position",
        outputs=(_s("Position", ST.VECTOR),),
    ),
    NodeSpec(
        "GeometryNodeInputNormal",
        "normal",
        "Normal",
        outputs=(_s("Normal", ST.VECTOR),),
    ),
    NodeSpec(
        "GeometryNodeInputIndex",
        "index",
        "Index",
        outputs=(_s("Index", ST.INT),),
    ),
    NodeSpec(
        "GeometryNodeInputID",
        "id_attr",
        "ID",
        outputs=(_s("ID", ST.INT),),
    ),
    NodeSpec(
        "GeometryNodeInputRadius",
        "radius",
        "Radius",
        outputs=(_s("Radius", ST.FLOAT),),
    ),
    NodeSpec(
        "GeometryNodeInputSceneTime",
        "scene_time",
        "Scene Time",
        outputs=(
            _s("Seconds", ST.FLOAT),
            _s("Frame", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexNoise",
        "noise_texture",
        "Noise Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Detail", ST.FLOAT, 2.0),
            _s("Roughness", ST.FLOAT, 0.5),
            _s("Lacunarity", ST.FLOAT, 2.0),
            _s("Distortion", ST.FLOAT, 0.0),
        ),
        outputs=(
            _s("Fac", ST.FLOAT),
            _s("Color", ST.COLOR),
        ),
        properties=(
            _p("noise_dimensions", "3D", "1D", "2D", "3D", "4D"),
            _p("noise_type", "FBM", "MULTIFRACTAL", "RIDGED_MULTIFRACTAL", "HYBRID_MULTIFRACTAL", "FBM", "HETERO_TERRAIN"),
            _p("normalize", True),
        ),
    ),
    NodeSpec(
        "ShaderNodeTexVoronoi",
        "voronoi_texture",
        "Voronoi Texture",
        inputs=(
            _s("Vector", ST.VECTOR, optional=True),
            _s("Scale", ST.FLOAT, 5.0),
            _s("Detail", ST.FLOAT, 0.0, optional=True),
            _s("Roughness", ST.FLOAT, 0.5, optional=True),
            _s("Lacunarity", ST.FLOAT, 2.0, optional=True),
            _s("Randomness", ST.FLOAT, 1.0),
        ),
        outputs=(
            _s("Distance", ST.FLOAT),
            _s("Color", ST.COLOR),
            _s("Position", ST.VECTOR),
        ),
        properties=(
            _p("voronoi_dimensions", "3D", "1D", "2D", "3D", "4D"),
            _p("feature", "F1", "F1", "F2", "SMOOTH_F1", "DISTANCE_TO_EDGE", "N_SPHERE_RADIUS"),
            _p("distance", "EUCLIDEAN", "EUCLIDEAN", "MANHATTAN", "CHEBYCHEV", "MINKOWSKI"),
        ),
    ),
    NodeSpec(
        "ShaderNodeMath",
        "math",
        "Math",
        inputs=(
            _s("Value", ST.FLOAT, 0.5),
            _s("Value_001", ST.FLOAT, 0.5),
            _s("Value_002", ST.FLOAT, 0.5, optional=True),
        ),
        outputs=(_s("Value", ST.FLOAT),),
        properties=(
            _p("operation", "ADD", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "MULTIPLY_ADD", "POWER", "LOGARITHM", "SQRT", "INVERSE_SQRT", "ABSOLUTE", "EXPONENT", "MINIMUM", "MAXIMUM", "LESS_THAN", "GREATER_THAN", "SIGN", "COMPARE", "SMOOTH_MIN", "SMOOTH_MAX", "ROUND", "FLOOR", "CEIL", "TRUNC", "FRACT", "MODULO", "FLOORED_MODULO", "WRAP", "SNAP", "PINGPONG", "SINE", "COSINE", "TANGENT", "ARCSINE", "ARCCOSINE", "ARCTANGENT", "ARCTAN2", "SINH", "COSH", "TANH", "RADIANS", "DEGREES"),
            _p("use_clamp", False),
        ),
    ),
    NodeSpec(
        "ShaderNodeVectorMath",
        "vector_math",
        "Vector Math",
        inputs=(
            _s("Vector", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Vector_001", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Vector_002", ST.VECTOR, (0.0, 0.0, 0.0), optional=True),
            _s("Scale", ST.FLOAT, 1.0, optional=True),
        ),
        outputs=(
            _s("Vector", ST.VECTOR),
            _s("Value", ST.FLOAT),
        ),
        properties=(
            _p("operation", "ADD", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE", "MULTIPLY_ADD", "CROSS_PRODUCT", "PROJECT", "REFLECT", "REFRACT", "FACEFORWARD", "DOT_PRODUCT", "DISTANCE", "LENGTH", "SCALE", "NORMALIZE", "ABSOLUTE", "MINIMUM", "MAXIMUM", "FLOOR", "CEIL", "FRACTION", "MODULO", "WRAP", "SNAP", "SINE", "COSINE", "TANGENT"),
        ),
    ),
    NodeSpec(
        "ShaderNodeMapRange",
        "map_range",
        "Map Range",
        inputs=(
            _s("Value", ST.FLOAT, 1.0),
            _s("From Min", ST.FLOAT, 0.0),
            _s("From Max", ST.FLOAT, 1.0),
            _s("To Min", ST.FLOAT, 0.0),
            _s("To Max", ST.FLOAT, 1.0),
            _s("Steps", ST.FLOAT, 4.0, optional=True),
        ),
        outputs=(_s("Result", ST.FLOAT),),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "FLOAT_VECTOR"),
            _p("interpolation_type", "LINEAR", "LINEAR", "STEPPED", "SMOOTHSTEP", "SMOOTHERSTEP"),
            _p("clamp", True),
        ),
    ),
    NodeSpec(
        "ShaderNodeClamp",
        "clamp",
        "Clamp",
        inputs=(
            _s("Value", ST.FLOAT, 1.0),
            _s("Min", ST.FLOAT, 0.0),
            _s("Max", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Result", ST.FLOAT),),
        properties=(_p("clamp_type", "MINMAX", "MINMAX", "RANGE"),),
    ),
    NodeSpec(
        "ShaderNodeMix",
        "mix",
        "Mix",
        inputs=(
            _s("Factor", ST.FLOAT, 0.5),
            _s("A", ST.FLOAT, 0.0),
            _s("B", ST.FLOAT, 0.0),
        ),
        outputs=(_s("Result", ST.FLOAT),),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "VECTOR", "RGBA", "ROTATION"),
            _p("clamp_factor", True),
            _p("clamp_result", False),
        ),
    ),
    NodeSpec(
        "FunctionNodeCompare",
        "compare",
        "Compare",
        inputs=(
            _s("A", ST.FLOAT, 0.0),
            _s("B", ST.FLOAT, 0.0),
            _s("C", ST.FLOAT, 0.9, optional=True),
            _s("Angle", ST.FLOAT, 0.0872665, optional=True),
            _s("Epsilon", ST.FLOAT, 0.001, optional=True),
        ),
        outputs=(_s("Result", ST.BOOLEAN),),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "INT", "VECTOR", "STRING", "RGBA"),
            _p("operation", "LESS_THAN", "LESS_THAN", "LESS_EQUAL", "GREATER_THAN", "GREATER_EQUAL", "EQUAL", "NOT_EQUAL"),
        ),
    ),
    NodeSpec(
        "FunctionNodeBooleanMath",
        "boolean_math",
        "Boolean Math",
        inputs=(
            _s("Boolean", ST.BOOLEAN, False),
            _s("Boolean_001", ST.BOOLEAN, False, optional=True),
        ),
        outputs=(_s("Boolean", ST.BOOLEAN),),
        properties=(_p("operation", "AND", "AND", "OR", "NOT", "NAND", "NOR", "XNOR", "XOR", "IMPLY", "NIMPLY"),),
    ),
    NodeSpec(
        "FunctionNodeRandomValue",
        "random_value",
        "Random Value",
        inputs=(
            _s("Min", ST.FLOAT, 0.0),
            _s("Max", ST.FLOAT, 1.0),
            _s("Probability", ST.FLOAT, 0.5, optional=True),
            _s("ID", ST.INT, optional=True),
            _s("Seed", ST.INT, 0),
        ),
        outputs=(_s("Value", ST.FLOAT),),
        properties=(_p("data_type", "FLOAT", "FLOAT", "INT", "FLOAT_VECTOR", "BOOLEAN"),),
    ),
    NodeSpec(
        "ShaderNodeSeparateXYZ",
        "separate_xyz",
        "Separate XYZ",
        inputs=(_s("Vector", ST.VECTOR, (0.0, 0.0, 0.0)),),
        outputs=(
            _s("X", ST.FLOAT),
            _s("Y", ST.FLOAT),
            _s("Z", ST.FLOAT),
        ),
    ),
    NodeSpec(
        "ShaderNodeCombineXYZ",
        "combine_xyz",
        "Combine XYZ",
        inputs=(
            _s("X", ST.FLOAT, 0.0),
            _s("Y", ST.FLOAT, 0.0),
            _s("Z", ST.FLOAT, 0.0),
        ),
        outputs=(_s("Vector", ST.VECTOR),),
    ),
    NodeSpec(
        "GeometryNodeSwitch",
        "switch",
        "Switch",
        inputs=(
            _s("Switch", ST.BOOLEAN, False),
            _s("False", ST.GEOMETRY, optional=True),
            _s("True", ST.GEOMETRY, optional=True),
        ),
        outputs=(_s("Output", ST.GEOMETRY),),
        properties=(_p("input_type", "GEOMETRY", "FLOAT", "INT", "BOOLEAN", "VECTOR", "ROTATION", "MATRIX", "STRING", "RGBA", "OBJECT", "IMAGE", "GEOMETRY", "COLLECTION", "TEXTURE", "MATERIAL"),),
    ),
    NodeSpec(
        "GeometryNodeCaptureAttribute",
        "capture_attribute",
        "Capture Attribute",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Value", ST.VECTOR, optional=True),
        ),
        outputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Attribute", ST.VECTOR),
        ),
        properties=(
            _p("data_type", "FLOAT_VECTOR", "FLOAT", "INT", "BOOLEAN", "FLOAT_VECTOR", "FLOAT_COLOR", "QUATERNION", "FLOAT4X4"),
            _p("domain", "POINT", "POINT", "EDGE", "FACE", "CORNER", "CURVE", "INSTANCE"),
        ),
    ),
    NodeSpec(
        "GeometryNodeStoreNamedAttribute",
        "store_named_attribute",
        "Store Named Attribute",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Name", ST.STRING, ""),
            _s("Value", ST.FLOAT, optional=True),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "INT", "BOOLEAN", "FLOAT_VECTOR", "FLOAT_COLOR", "QUATERNION", "FLOAT4X4"),
            _p("domain", "POINT", "POINT", "EDGE", "FACE", "CORNER", "CURVE", "INSTANCE"),
        ),
    ),
    NodeSpec(
        "GeometryNodeNamedAttribute",
        "named_attribute",
        "Named Attribute",
        inputs=(_s("Name", ST.STRING, ""),),
        outputs=(
            _s("Attribute", ST.FLOAT),
            _s("Exists", ST.BOOLEAN),
        ),
        properties=(_p("data_type", "FLOAT", "FLOAT", "INT", "BOOLEAN", "FLOAT_VECTOR", "FLOAT_COLOR", "QUATERNION", "FLOAT4X4"),),
    ),
    NodeSpec(
        "FunctionNodeFloatToInt",
        "float_to_int",
        "Float to Integer",
        inputs=(_s("Float", ST.FLOAT, 0.0),),
        outputs=(_s("Integer", ST.INT),),
        properties=(_p("rounding_mode", "ROUND", "ROUND", "FLOOR", "CEILING", "TRUNCATE"),),
    ),
    NodeSpec(
        "GeometryNodeViewer",
        "viewer",
        "Viewer",
        inputs=(
            _s("Geometry", ST.GEOMETRY, optional=True),
            _s("Value", ST.FLOAT, optional=True),
        ),
        properties=(
            _p("data_type", "FLOAT", "FLOAT", "INT", "BOOLEAN", "VECTOR", "ROTATION", "MATRIX", "RGBA"),
            _p("domain", "AUTO", "AUTO", "POINT", "EDGE", "FACE", "CORNER", "CURVE", "INSTANCE"),
        ),
    ),
    NodeSpec(
        "NodeReroute",
        "reroute",
        "Reroute",
        inputs=(_s("Input", ST.GEOMETRY),),
        outputs=(_s("Output", ST.GEOMETRY),),
    ),
    NodeSpec(
        "NodeFrame",
        "frame",
        "Frame",
        properties=(
            _p("label_size", 20),
            _p("shrink", True),
        ),
    ),
    NodeSpec(
        "GeometryNodeTranslateInstances",
        "translate_instances",
        "Translate Instances",
        inputs=(
            _s("Instances", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Translation", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Local Space", ST.BOOLEAN, True),
        ),
        outputs=(_s("Instances", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeRotateInstances",
        "rotate_instances",
        "Rotate Instances",
        inputs=(
            _s("Instances", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Rotation", ST.ROTATION, (0.0, 0.0, 0.0)),
            _s("Pivot Point", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Local Space", ST.BOOLEAN, True),
        ),
        outputs=(_s("Instances", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeScaleInstances",
        "scale_instances",
        "Scale Instances",
        inputs=(
            _s("Instances", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Scale", ST.VECTOR, (1.0, 1.0, 1.0)),
            _s("Center", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Local Space", ST.BOOLEAN, True),
        ),
        outputs=(_s("Instances", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeScaleElements",
        "scale_elements",
        "Scale Elements",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Scale", ST.FLOAT, 1.0),
            _s("Center", ST.VECTOR, optional=True),
            _s("Axis", ST.VECTOR, (1.0, 0.0, 0.0), optional=True),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
        properties=(
            _p("domain", "FACE", "FACE", "EDGE"),
            _p("scale_mode", "UNIFORM", "UNIFORM", "SINGLE_AXIS"),
        ),
    ),
    NodeSpec(
        "GeometryNodeSplitEdges",
        "split_edges",
        "Split Edges",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeTriangulate",
        "triangulate",
        "Triangulate",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Minimum Vertices", ST.INT, 4),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
        properties=(
            _p("quad_method", "SHORTEST_DIAGONAL", "BEAUTY", "FIXED", "FIXED_ALTERNATE", "SHORTEST_DIAGONAL", "LONGEST_DIAGONAL"),
            _p("ngon_method", "BEAUTY", "BEAUTY", "CLIP"),
        ),
    ),
    NodeSpec(
        "GeometryNodeFlipFaces",
        "flip_faces",
        "Flip Faces",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
        ),
        outputs=(_s("Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeDualMesh",
        "dual_mesh",
        "Dual Mesh",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Keep Boundaries", ST.BOOLEAN, False),
        ),
        outputs=(_s("Dual Mesh", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeMeshToPoints",
        "mesh_to_points",
        "Mesh to Points",
        inputs=(
            _s("Mesh", ST.GEOMETRY),
            _s("Selection", ST.BOOLEAN, True, optional=True),
            _s("Position", ST.VECTOR, optional=True),
            _s("Radius", ST.FLOAT, 0.05),
        ),
        outputs=(_s("Points", ST.GEOMETRY),),
        properties=(_p("mode", "VERTICES", "VERTICES", "EDGES", "FACES", "CORNERS"),),
    ),
    NodeSpec(
        "GeometryNodePoints",
        "points",
        "Points",
        inputs=(
            _s("Count", ST.INT, 1),
            _s("Position", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("Radius", ST.FLOAT, 0.05),
        ),
        outputs=(_s("Geometry", ST.GEOMETRY),),
    ),
    NodeSpec(
        "GeometryNodeFilletCurve",
        "fillet_curve",
        "Fillet Curve",
        inputs=(
            _s("Curve", ST.GEOMETRY),
            _s("Count", ST.INT, 1, optional=True),
            _s("Radius", ST.FLOAT, 0.25),
            _s("Limit Radius", ST.BOOLEAN, False),
        ),
        outputs=(_s("Curve", ST.GEOMETRY),),
        properties=(_p("mode", "BEZIER", "BEZIER", "POLY"),),
    ),
    NodeSpec(
        "GeometryNodeCurvePrimitiveCircle",
        "curve_circle",
        "Curve Circle",
        inputs=(
            _s("Resolution", ST.INT, 32),
            _s("Radius", ST.FLOAT, 1.0),
        ),
        outputs=(_s("Curve", ST.GEOMETRY),),
        properties=(_p("mode", "RADIUS", "POINTS", "RADIUS"),),
    ),
    NodeSpec(
        "GeometryNodeCurvePrimitiveLine",
        "curve_line",
        "Curve Line",
        inputs=(
            _s("Start", ST.VECTOR, (0.0, 0.0, 0.0)),
            _s("End", ST.VECTOR, (0.0, 0.0, 1.0)),
            _s("Direction", ST.VECTOR, (0.0, 0.0, 1.0), optional=True),
            _s("Length", ST.FLOAT, 1.0, optional=True),
        ),
        outputs=(_s("Curve", ST.GEOMETRY),),
        properties=(_p("mode", "POINTS", "POINTS", "DIRECTION"),),
    ),
    NodeSpec(
        "GeometryNodeAlignRotationToVector",
        "align_rotation_to_vector",
        "Align Rotation to Vector",
        inputs=(
            _s("Rotation", ST.ROTATION, (0.0, 0.0, 0.0), optional=True),
            _s("Factor", ST.FLOAT, 1.0),
            _s("Vector", ST.VECTOR, (0.0, 0.0, 1.0)),
        ),
        outputs=(_s("Rotation", ST.ROTATION),),
        properties=(
            _p("axis", "X", "X", "Y", "Z"),
            _p("pivot_axis", "AUTO", "AUTO", "X", "Y", "Z"),
        ),
    ),
    NodeSpec(
        "GeometryNodeProximity",
        "proximity",
        "Geometry Proximity",
        inputs=(
            _s("Geometry", ST.GEOMETRY),
            _s("Sample Position", ST.VECTOR, optional=True),
        ),
        outputs=(
            _s("Position", ST.VECTOR),
            _s("Distance", ST.FLOAT),
        ),
        properties=(_p("target_element", "FACES", "POINTS", "EDGES", "FACES"),),
    ),
)

CATALOG: tuple[NodeSpec, ...] = _SPECS
CATALOG_BY_TYPE: dict[str, NodeSpec] = {spec.bl_idname: spec for spec in _SPECS}
CATALOG_BY_METHOD: dict[str, NodeSpec] = {spec.method: spec for spec in _SPECS}


def get_spec(bl_idname: str) -> NodeSpec | None:
    return CATALOG_BY_TYPE.get(bl_idname)


def values_equal(left: Any, right: Any) -> bool:
    if left == right:
        return True
    if isinstance(left, (list, tuple)) and isinstance(right, (list, tuple)):
        if len(left) != len(right):
            return False
        return all(values_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-9
    return False
