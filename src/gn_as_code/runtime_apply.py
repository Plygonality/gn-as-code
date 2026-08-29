"""Self-contained bpy apply/dump runtime.

This module has no gn-as-code imports so it can be exec'd inside Blender via
Plygon-mcp ``execute_blender_code``. The graph JSON is the source of truth;
the .blend is the cache.
"""

from __future__ import annotations

FORMAT = "gn-as-code"
FORMAT_VERSION = 1

_SOCKET_BL_IDNAME = {
    "FLOAT": "NodeSocketFloat",
    "INT": "NodeSocketInt",
    "BOOLEAN": "NodeSocketBoolean",
    "VECTOR": "NodeSocketVector",
    "ROTATION": "NodeSocketRotation",
    "MATRIX": "NodeSocketMatrix",
    "COLOR": "NodeSocketColor",
    "STRING": "NodeSocketString",
    "GEOMETRY": "NodeSocketGeometry",
    "OBJECT": "NodeSocketObject",
    "COLLECTION": "NodeSocketCollection",
    "MATERIAL": "NodeSocketMaterial",
    "TEXTURE": "NodeSocketTexture",
    "IMAGE": "NodeSocketImage",
    "MENU": "NodeSocketMenu",
}

_SOCKET_FROM_BL = {
    "NodeSocketFloat": "FLOAT",
    "NodeSocketFloatFactor": "FLOAT",
    "NodeSocketFloatAngle": "FLOAT",
    "NodeSocketFloatDistance": "FLOAT",
    "NodeSocketFloatUnsigned": "FLOAT",
    "NodeSocketInt": "INT",
    "NodeSocketIntUnsigned": "INT",
    "NodeSocketBool": "BOOLEAN",
    "NodeSocketBoolean": "BOOLEAN",
    "NodeSocketVector": "VECTOR",
    "NodeSocketVectorEuler": "VECTOR",
    "NodeSocketVectorXYZ": "VECTOR",
    "NodeSocketVectorTranslation": "VECTOR",
    "NodeSocketVectorDirection": "VECTOR",
    "NodeSocketRotation": "ROTATION",
    "NodeSocketMatrix": "MATRIX",
    "NodeSocketColor": "COLOR",
    "NodeSocketString": "STRING",
    "NodeSocketGeometry": "GEOMETRY",
    "NodeSocketObject": "OBJECT",
    "NodeSocketCollection": "COLLECTION",
    "NodeSocketMaterial": "MATERIAL",
    "NodeSocketTexture": "TEXTURE",
    "NodeSocketImage": "IMAGE",
    "NodeSocketMenu": "MENU",
}

_NODE_SKIP_PROPS = {
    "rna_type",
    "type",
    "bl_idname",
    "bl_label",
    "bl_description",
    "bl_icon",
    "bl_static_type",
    "bl_width_default",
    "bl_width_min",
    "bl_width_max",
    "bl_height_default",
    "bl_height_min",
    "bl_height_max",
    "name",
    "label",
    "location",
    "location_absolute",
    "width",
    "height",
    "dimensions",
    "inputs",
    "outputs",
    "internal_links",
    "parent",
    "select",
    "show_options",
    "show_preview",
    "show_texture",
    "hide",
    "mute",
    "use_custom_color",
    "color",
    "width_hidden",
    "warning_propagation",
}


def apply_graph_dict(
    data,
    bpy,
    *,
    object_name=None,
    modifier_name="GeometryNodes",
    replace=True,
):
    """Rebuild a Geometry Node tree from a gn-as-code dump.

    Returns the node group. If ``object_name`` is set, a NODES modifier is
    attached (the object is created as an empty mesh if missing).
    """
    _validate_payload(data)
    name = data["name"]
    tree = bpy.data.node_groups.get(name)
    if tree is None:
        tree = bpy.data.node_groups.new(name, "GeometryNodeTree")
    elif not replace:
        raise ValueError(f"Node group {name!r} already exists")
    _set_kind(tree, data.get("kind", "MODIFIER"))
    _clear_tree(tree)
    _build_interface(tree, data.get("interface") or {})
    created = _build_nodes(tree, data.get("nodes") or [])
    _build_links(tree, data.get("links") or [], created)
    if object_name:
        _attach_modifier(bpy, object_name, tree, modifier_name)
    return tree


def dump_tree(tree, *, blender="4.2"):
    """Serialize a live GeometryNodeTree into a gn-as-code dict."""
    interface = _dump_interface(tree)
    nodes = [_dump_node(node) for node in tree.nodes]
    links = [_dump_link(link) for link in tree.links]
    kind = "MODIFIER"
    if getattr(tree, "is_tool", False):
        kind = "TOOL"
    elif getattr(tree, "is_modifier", True) is False:
        kind = "GROUP"
    nodes_sorted = sorted(nodes, key=lambda n: n["id"])
    links_sorted = sorted(
        links,
        key=lambda ln: (ln["from"][0], ln["from"][1], ln["to"][0], ln["to"][1]),
    )
    return {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "name": tree.name,
        "kind": kind,
        "blender": blender,
        "interface": interface,
        "nodes": nodes_sorted,
        "links": links_sorted,
    }


def dump_tree_by_name(bpy, name, *, blender="4.2"):
    tree = bpy.data.node_groups.get(name)
    if tree is None:
        raise KeyError(f"No node group named {name!r}")
    return dump_tree(tree, blender=blender)


def _validate_payload(data):
    if data.get("format") not in (None, FORMAT):
        raise ValueError(f"Unsupported graph format: {data.get('format')!r}")
    version = data.get("version", FORMAT_VERSION)
    if int(version) != FORMAT_VERSION:
        raise ValueError(f"Unsupported gn-as-code version: {version}")
    if "name" not in data:
        raise ValueError("Graph dump is missing 'name'")


def _set_kind(tree, kind):
    if hasattr(tree, "is_modifier"):
        tree.is_modifier = kind == "MODIFIER"
    if hasattr(tree, "is_tool"):
        tree.is_tool = kind == "TOOL"


def _clear_tree(tree):
    tree.nodes.clear()
    interface = getattr(tree, "interface", None)
    if interface is None:
        return
    clearer = getattr(interface, "clear", None)
    if callable(clearer):
        clearer()
        return
    items = list(getattr(interface, "items_tree", []))
    for item in items:
        try:
            interface.remove(item)
        except Exception:
            pass


def _build_interface(tree, interface):
    iface = getattr(tree, "interface", None)
    if iface is None:
        return
    for item in interface.get("inputs", []):
        _add_interface_socket(iface, item, "INPUT")
    for item in interface.get("outputs", []):
        _add_interface_socket(iface, item, "OUTPUT")


def _add_interface_socket(iface, item, in_out):
    socket_type = _SOCKET_BL_IDNAME.get(item.get("socket", "GEOMETRY"), "NodeSocketGeometry")
    sock = iface.new_socket(name=item["name"], in_out=in_out, socket_type=socket_type)
    if item.get("default") is not None and hasattr(sock, "default_value"):
        _set_value(sock, "default_value", item["default"])
    if item.get("min") is not None and hasattr(sock, "min_value"):
        sock.min_value = item["min"]
    if item.get("max") is not None and hasattr(sock, "max_value"):
        sock.max_value = item["max"]
    if item.get("subtype") and hasattr(sock, "subtype"):
        sock.subtype = item["subtype"]
    if item.get("description") and hasattr(sock, "description"):
        sock.description = item["description"]
    return sock


def _build_nodes(tree, nodes):
    created = {}
    # Frames first so children can set parent.
    ordered = sorted(nodes, key=lambda n: 0 if n.get("type") == "NodeFrame" else 1)
    for spec in ordered:
        node = tree.nodes.new(spec["type"])
        node.name = spec["id"]
        if spec.get("label"):
            node.label = spec["label"]
        if spec.get("hide"):
            node.hide = True
        if spec.get("mute"):
            node.mute = True
        if spec.get("location") is not None:
            node.location = tuple(spec["location"])
        for key, value in (spec.get("properties") or {}).items():
            _set_value(node, key, value)
        for key, value in (spec.get("inputs") or {}).items():
            socket = _find_socket(node.inputs, key)
            if socket is not None:
                _set_value(socket, "default_value", value)
        created[spec["id"]] = node
    for spec in ordered:
        parent_id = spec.get("parent")
        if parent_id and parent_id in created:
            created[spec["id"]].parent = created[parent_id]
    return created


def _build_links(tree, links, created):
    for spec in links:
        src_id, src_sock = spec["from"]
        dst_id, dst_sock = spec["to"]
        src = created.get(src_id)
        dst = created.get(dst_id)
        if src is None or dst is None:
            raise KeyError(f"Link references missing node: {src_id!r} -> {dst_id!r}")
        from_socket = _find_socket(src.outputs, src_sock)
        to_socket = _find_socket(dst.inputs, dst_sock)
        if from_socket is None or to_socket is None:
            raise KeyError(
                f"Link sockets not found: {src_id}.{src_sock} -> {dst_id}.{dst_sock}"
            )
        tree.links.new(from_socket, to_socket)


def _attach_modifier(bpy, object_name, tree, modifier_name):
    obj = bpy.data.objects.get(object_name)
    if obj is None:
        mesh = bpy.data.meshes.new(object_name)
        obj = bpy.data.objects.new(object_name, mesh)
        collection = bpy.context.scene.collection
        collection.objects.link(obj)
    existing = obj.modifiers.get(modifier_name)
    if existing is not None and getattr(existing, "type", None) == "NODES":
        existing.node_group = tree
        return existing
    mod = obj.modifiers.new(modifier_name, "NODES")
    mod.node_group = tree
    return mod


def _find_socket(sockets, key):
    if isinstance(key, int) or (isinstance(key, str) and key.isdigit()):
        index = int(key)
        if 0 <= index < len(sockets):
            return sockets[index]
        return None
    for socket in sockets:
        if getattr(socket, "identifier", None) == key:
            return socket
    for socket in sockets:
        if getattr(socket, "name", None) == key:
            return socket
    return None


def _set_value(owner, attr, value):
    if not hasattr(owner, attr):
        return
    current = getattr(owner, attr)
    try:
        setattr(owner, attr, value)
        return
    except Exception:
        pass
    if isinstance(value, (list, tuple)) and current is not None:
        try:
            if hasattr(current, "foreach_set"):
                current.foreach_set(list(value))
                return
        except Exception:
            pass
        try:
            for i, part in enumerate(value):
                current[i] = part
            return
        except Exception:
            pass
        if len(value) == 3:
            try:
                setattr(owner, attr, (*value, 1.0))
            except Exception:
                pass


def _dump_interface(tree):
    inputs = []
    outputs = []
    iface = getattr(tree, "interface", None)
    if iface is None:
        return {"inputs": inputs, "outputs": outputs}
    items = list(getattr(iface, "items_tree", []))
    for item in items:
        item_type = getattr(item, "item_type", "SOCKET")
        if item_type not in ("SOCKET", None) and item_type != "SOCKET":
            continue
        in_out = getattr(item, "in_out", None)
        if in_out not in ("INPUT", "OUTPUT"):
            continue
        payload = {
            "name": item.name,
            "socket": _socket_kind(getattr(item, "socket_type", None) or getattr(item, "bl_socket_idname", "GEOMETRY")),
        }
        if hasattr(item, "default_value"):
            dumped = _jsonify(item.default_value)
            if dumped is not None:
                payload["default"] = dumped
        if hasattr(item, "min_value"):
            payload["min"] = _jsonify(item.min_value)
        if hasattr(item, "max_value"):
            payload["max"] = _jsonify(item.max_value)
        if getattr(item, "description", ""):
            payload["description"] = item.description
        if in_out == "INPUT":
            inputs.append(payload)
        else:
            outputs.append(payload)
    return {"inputs": inputs, "outputs": outputs}


def _dump_node(node):
    payload = {
        "id": node.name,
        "type": getattr(node, "bl_idname", None) or node.type,
    }
    if getattr(node, "label", ""):
        payload["label"] = node.label
    loc = getattr(node, "location", None)
    if loc is not None:
        payload["location"] = [_jsonify(loc[0]), _jsonify(loc[1])]
    if getattr(node, "hide", False):
        payload["hide"] = True
    if getattr(node, "mute", False):
        payload["mute"] = True
    parent = getattr(node, "parent", None)
    if parent is not None:
        payload["parent"] = parent.name
    inputs = {}
    for socket in node.inputs:
        if getattr(socket, "is_linked", False):
            continue
        if not hasattr(socket, "default_value"):
            continue
        ident = getattr(socket, "identifier", None) or socket.name
        try:
            inputs[ident] = _jsonify(socket.default_value)
        except Exception:
            continue
    if inputs:
        payload["inputs"] = inputs
    properties = _dump_properties(node)
    if properties:
        payload["properties"] = properties
    return payload


def _dump_properties(node):
    props = {}
    bl_rna = getattr(node, "bl_rna", None)
    if bl_rna is None:
        for key, value in getattr(node, "properties", {}).items():
            props[key] = _jsonify(value)
        return props
    for prop in bl_rna.properties:
        ident = prop.identifier
        if ident in _NODE_SKIP_PROPS or getattr(prop, "is_readonly", False):
            continue
        try:
            value = getattr(node, ident)
        except Exception:
            continue
        dumped = _jsonify(value)
        if dumped is None or callable(dumped):
            continue
        props[ident] = dumped
    return props


def _dump_link(link):
    return {
        "from": [
            link.from_node.name,
            getattr(link.from_socket, "identifier", None) or link.from_socket.name,
        ],
        "to": [
            link.to_node.name,
            getattr(link.to_socket, "identifier", None) or link.to_socket.name,
        ],
    }


def _socket_kind(bl_idname):
    if not bl_idname:
        return "GEOMETRY"
    if bl_idname in _SOCKET_FROM_BL:
        return _SOCKET_FROM_BL[bl_idname]
    key = str(bl_idname).replace("NodeSocket", "").upper()
    if key in _SOCKET_BL_IDNAME:
        return key
    return str(bl_idname)


def _jsonify(value):
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        rounded = round(float(value), 6)
        return int(rounded) if rounded == int(rounded) else rounded
    if isinstance(value, bytes):
        return value.decode("utf-8")
    to_list = getattr(value, "to_list", None)
    if callable(to_list):
        return _jsonify(to_list())
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    if hasattr(value, "x") and hasattr(value, "y"):
        parts = [value.x, value.y]
        if hasattr(value, "z"):
            parts.append(value.z)
        if hasattr(value, "w"):
            parts.append(value.w)
        return _jsonify(parts)
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name
    identifier = getattr(value, "identifier", None)
    if isinstance(identifier, str) and identifier not in ("rna_type",):
        return identifier
    return None
