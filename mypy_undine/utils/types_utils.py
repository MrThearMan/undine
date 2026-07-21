from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import DirectiveLocation
from mypy.nodes import FuncDef, ListExpr, MemberExpr, NameExpr, StrExpr
from mypy.subtypes import is_same_type
from mypy.types import Instance, TypeType, get_proper_type

from mypy_undine.fullnames import FILTER_SET, INTERFACE_TYPE, MUTATION_TYPE, ORDER_SET, QUERY_TYPE, UNION_TYPE

if TYPE_CHECKING:
    from mypy.nodes import ClassDef, Expression, TypeInfo
    from mypy.types import ProperType, Type


def query_type_model(typ: ProperType) -> Type | None:
    if not isinstance(typ, Instance):
        return None
    if typ.type.fullname != QUERY_TYPE or not typ.args:
        return None
    return typ.args[0]


def query_type_model_from_class(info: TypeInfo) -> Type | None:
    for base in info.bases:
        found = query_type_model(get_proper_type(base))
        if found is not None:
            return found
    return None


def mutation_type_model(typ: ProperType) -> Type | None:
    if not isinstance(typ, Instance):
        return None
    if typ.type.fullname != MUTATION_TYPE:
        return None
    if not typ.args:
        return None
    return typ.args[0]


def mutation_type_model_from_class(info: TypeInfo) -> Type | None:
    for base in info.bases:
        found = mutation_type_model(get_proper_type(base))
        if found is not None:
            return found
    return None


def filterset_models(typ: ProperType) -> list[Type] | None:
    if not isinstance(typ, Instance):
        return None
    if typ.type.fullname != FILTER_SET:
        return None
    return list(typ.args)


def filterset_models_from_class(info: TypeInfo) -> list[Type] | None:
    for base in info.bases:
        found = filterset_models(get_proper_type(base))
        if found is not None:
            return found
    return None


def orderset_models(typ: ProperType) -> list[Type] | None:
    if not isinstance(typ, Instance):
        return None
    if typ.type.fullname != ORDER_SET:
        return None
    return list(typ.args)


def orderset_models_from_class(info: TypeInfo) -> list[Type] | None:
    for base in info.bases:
        found = orderset_models(get_proper_type(base))
        if found is not None:
            return found
    return None


def union_query_type_infos(typ: ProperType) -> list[TypeInfo] | None:
    if not isinstance(typ, Instance):
        return None
    if typ.type.fullname != UNION_TYPE or not typ.args:
        return None
    out: list[TypeInfo] = []
    for arg in typ.args:
        ap = get_proper_type(arg)
        if isinstance(ap, TypeType):
            item = get_proper_type(ap.item)
            if isinstance(item, Instance):
                out.append(item.type)
            else:
                return None
        elif isinstance(ap, Instance):
            out.append(ap.type)
        else:
            return None
    return out


def union_member_model_ids(info: TypeInfo) -> frozenset[str] | None:
    for base in info.bases:
        ut = union_query_type_infos(get_proper_type(base))
        if ut is None:
            continue
        ids: list[str] = []
        for qti in ut:
            m = query_type_model_from_class(qti)
            if m is None:
                return None
            ids.append(type_fingerprint(m))
        return frozenset(ids)
    return None


def type_fingerprint(t: Type) -> str:
    p = get_proper_type(t)
    if isinstance(p, Instance):
        return p.type.fullname
    return str(p)


def models_match(a: Type, b: Type) -> bool:
    return is_same_type(get_proper_type(a), get_proper_type(b))


def supports_interfaces(info: TypeInfo) -> bool:
    return any(cls.fullname in {INTERFACE_TYPE, QUERY_TYPE} for cls in info.mro)


DIRECTIVE_METADATA_KEY = "undine_directive"


def stash_directive_metadata(info: TypeInfo) -> None:
    """
    Persist directive `locations` / `is_repeatable` from class keywords into `info.metadata`.

    Called from the base_class_hook while `info.defn.keywords` is still populated.
    Reading from metadata is serialization-safe (`info.defn` loses its keywords when a
    module is loaded from mypy's incremental cache), so downstream lookups should
    consult metadata as the source of truth and fall back to `defn.keywords`.
    """
    data: dict[str, object] = {}

    locations_expr = info.defn.keywords.get("locations")
    if isinstance(locations_expr, ListExpr):
        locations: list[str] = []
        for item in locations_expr.items:
            if isinstance(item, StrExpr):
                try:
                    locations.append(DirectiveLocation(item.value).name)
                except ValueError:
                    continue
                continue
            if isinstance(item, MemberExpr):
                try:
                    locations.append(DirectiveLocation[item.name].name)
                except KeyError:
                    continue
        data["locations"] = locations

    repeatable_expr = info.defn.keywords.get("is_repeatable")
    if isinstance(repeatable_expr, NameExpr):
        data["is_repeatable"] = repeatable_expr.fullname == "builtins.True"

    if data:
        info.metadata[DIRECTIVE_METADATA_KEY] = data


def directive_locations_from_class(info: TypeInfo) -> set[DirectiveLocation]:
    metadata = info.metadata.get(DIRECTIVE_METADATA_KEY)
    if isinstance(metadata, dict):
        cached = metadata.get("locations")
        if isinstance(cached, list):
            result: set[DirectiveLocation] = set()
            for name in cached:
                if not isinstance(name, str):
                    continue
                try:
                    result.add(DirectiveLocation[name])
                except KeyError:
                    continue
            return result

    location: Expression | None = info.defn.keywords.get("locations")
    if location is None:
        return set()

    if not isinstance(location, ListExpr):
        return set()

    locations: set[DirectiveLocation] = set()
    for item in location.items:
        if isinstance(item, StrExpr):
            locations.add(DirectiveLocation(item.value))
            continue

        if isinstance(item, MemberExpr):
            locations.add(DirectiveLocation[item.name])
            continue

    return locations


def is_repeatable_from_class(info: TypeInfo) -> bool:
    metadata = info.metadata.get(DIRECTIVE_METADATA_KEY)
    if isinstance(metadata, dict) and "is_repeatable" in metadata:
        return bool(metadata["is_repeatable"])

    location: Expression | None = info.defn.keywords.get("is_repeatable")
    if location is None:
        return False

    if not isinstance(location, NameExpr):
        return False

    return location.fullname == "builtins.True"


def has_init(cls_def: ClassDef) -> bool:
    for expr in cls_def.defs.body:
        if not isinstance(expr, FuncDef):
            continue

        if expr.name == "__init__":
            return True

    return False
