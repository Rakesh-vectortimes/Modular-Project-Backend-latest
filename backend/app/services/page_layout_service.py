from __future__ import annotations

from pymongo.database import Database

from app.db.mongo import new_object_id, oid
from app.db.serialize import prepare_insert, prepare_update
from app.schemas.layout import (
    LayoutNodeRead,
    LayoutNodeWrite,
    PageLayoutRead,
    PageSettings,
    PublishedLayoutRead,
)
from app.services import entity_service


class PageLayoutNotFoundError(Exception):
    pass


class InvalidLayoutError(Exception):
    pass


def _settings_from_page(page: dict) -> PageSettings:
    raw = page.get("settings") or {}
    if not isinstance(raw, dict):
        return PageSettings()
    try:
        width = int(raw.get("viewportWidth") or 1280)
    except (TypeError, ValueError):
        width = 1280
    try:
        height = int(raw.get("viewportHeight") or 800)
    except (TypeError, ValueError):
        height = 800
    return PageSettings(
        backgroundColor=str(raw.get("backgroundColor") or "#f4f6f9"),
        backgroundImage=str(raw.get("backgroundImage") or ""),
        viewportWidth=max(320, min(width, 3840)),
        viewportHeight=max(240, min(height, 2160)),
    )


def get_page_layout(db: Database, page_id: str) -> PageLayoutRead:
    page = db.pages.find_one({"_id": oid(page_id)})
    if page is None:
        raise PageLayoutNotFoundError(f"Page {page_id} not found")

    components = list(db.page_components.find({"page_id": page_id}))
    tree = build_tree_from_flat(components)
    return PageLayoutRead(
        page_id=page_id,
        components=tree,
        settings=_settings_from_page(page),
    )


def get_published_layout(
    db: Database, software_id: str, page_id: str | None = None
) -> PublishedLayoutRead:
    if page_id:
        page = db.pages.find_one({"_id": oid(page_id), "software_id": software_id})
        if page is None:
            raise PageLayoutNotFoundError(
                f"Page {page_id} not found for software {software_id}"
            )
    else:
        page = db.pages.find_one({"software_id": software_id, "is_default": True})
        if page is None:
            raise PageLayoutNotFoundError(f"No default page found for software {software_id}")

    resolved_page_id = str(page["_id"])
    layout = get_page_layout(db, resolved_page_id)
    return PublishedLayoutRead(
        software_id=software_id,
        page_id=resolved_page_id,
        page_name=page["name"],
        components=layout.components,
        settings=layout.settings,
    )


def replace_page_layout(
    db: Database,
    page_id: str,
    components: list[LayoutNodeWrite],
    settings: PageSettings | None = None,
) -> PageLayoutRead:
    page = db.pages.find_one({"_id": oid(page_id)})
    if page is None:
        raise PageLayoutNotFoundError(f"Page {page_id} not found")

    flat_nodes = flatten_tree(components)
    _validate_flat_layout(flat_nodes)

    existing_ids = {
        str(doc["_id"])
        for doc in db.page_components.find({"page_id": page_id}, {"_id": 1})
    }
    incoming_ids = {node.id for node in flat_nodes if node.id is not None}
    ids_to_delete = existing_ids - incoming_ids

    if ids_to_delete:
        db.page_components.delete_many(
            {"_id": {"$in": [oid(component_id) for component_id in ids_to_delete]}}
        )

    id_map: dict[int | None, str] = {}

    for node in flat_nodes:
        parent_db_id = id_map.get(node.parent_temp_id)

        if node.id is not None and node.id in existing_ids:
            existing = db.page_components.find_one({"_id": oid(node.id)})
            if existing is None or existing.get("page_id") != page_id:
                raise InvalidLayoutError(f"Component {node.id} does not belong to page {page_id}")

            db.page_components.update_one(
                {"_id": oid(node.id)},
                {
                    "$set": prepare_update(
                        {
                            "parent_id": parent_db_id,
                            "component_type": node.component_type,
                            "props": node.props,
                            "position": node.position,
                            "order": node.order,
                        }
                    )
                },
            )
            db_id = node.id
        else:
            new_id = new_object_id()
            db.page_components.insert_one(
                prepare_insert(
                    {
                        "_id": new_id,
                        "page_id": page_id,
                        "parent_id": parent_db_id,
                        "component_type": node.component_type,
                        "props": node.props,
                        "position": node.position,
                        "order": node.order,
                    }
                )
            )
            db_id = str(new_id)

        id_map[node.temp_id] = db_id

    if settings is not None:
        db.pages.update_one(
            {"_id": oid(page_id)},
            {
                "$set": prepare_update(
                    {
                        "settings": settings.model_dump(),
                    }
                )
            },
        )

    layout = get_page_layout(db, page_id)

    # Auto-create/update the reusable entity (table) this page's form is bound
    # to, from the input components now present in the saved layout. Pages that
    # share an entity name share one collection (design doc: Reusable Entities).
    entity_service.sync_page_entity(db, page_id)

    return layout


def build_tree_from_flat(components: list[dict]) -> list[LayoutNodeRead]:
    by_parent: dict[str | None, list[dict]] = {}
    for component in components:
        by_parent.setdefault(component.get("parent_id"), []).append(component)

    for siblings in by_parent.values():
        siblings.sort(key=lambda c: (c.get("order", 0), str(c["_id"])))

    def build_branch(parent_id: str | None) -> list[LayoutNodeRead]:
        nodes: list[LayoutNodeRead] = []
        for component in by_parent.get(parent_id, []):
            component_id = str(component["_id"])
            nodes.append(
                LayoutNodeRead(
                    id=component_id,
                    component_type=component["component_type"],
                    props=component.get("props") or {},
                    position=component.get("position") or {},
                    order=component.get("order", 0),
                    children=build_branch(component_id),
                )
            )
        return nodes

    return build_branch(None)


class _FlatNode:
    __slots__ = (
        "id",
        "temp_id",
        "parent_temp_id",
        "component_type",
        "props",
        "position",
        "order",
    )

    def __init__(
        self,
        *,
        id: str | None,
        temp_id: int,
        parent_temp_id: int | None,
        component_type: str,
        props: dict,
        position: dict,
        order: int,
    ):
        self.id = id
        self.temp_id = temp_id
        self.parent_temp_id = parent_temp_id
        self.component_type = component_type
        self.props = props
        self.position = position
        self.order = order


def flatten_tree(
    nodes: list[LayoutNodeWrite], parent_temp_id: int | None = None, counter: list[int] | None = None
) -> list[_FlatNode]:
    if counter is None:
        counter = [0]

    flat: list[_FlatNode] = []
    for node in nodes:
        counter[0] += 1
        temp_id = counter[0]
        flat.append(
            _FlatNode(
                id=node.id,
                temp_id=temp_id,
                parent_temp_id=parent_temp_id,
                component_type=node.component_type,
                props=node.props,
                position=node.position.model_dump(),
                order=node.order,
            )
        )
        flat.extend(flatten_tree(node.children, temp_id, counter))
    return flat


def _validate_flat_layout(flat_nodes: list[_FlatNode]) -> None:
    seen_ids: set[str] = set()
    for node in flat_nodes:
        if node.id is not None:
            if node.id in seen_ids:
                raise InvalidLayoutError(f"Duplicate component id in layout: {node.id}")
            seen_ids.add(node.id)

        if not node.component_type:
            raise InvalidLayoutError("Each layout node must have a component_type")
