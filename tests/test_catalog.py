from __future__ import annotations

from gn_as_code.catalog import CATALOG, CATALOG_BY_METHOD, CATALOG_BY_TYPE


def test_catalog_ids_unique() -> None:
    types = [s.bl_idname for s in CATALOG]
    methods = [s.method for s in CATALOG]
    assert len(types) == len(set(types))
    assert len(methods) == len(set(methods))
    assert CATALOG_BY_TYPE["GeometryNodeMeshCube"].method == "mesh_cube"
    assert CATALOG_BY_METHOD["instance_on_points"].bl_idname == "GeometryNodeInstanceOnPoints"
