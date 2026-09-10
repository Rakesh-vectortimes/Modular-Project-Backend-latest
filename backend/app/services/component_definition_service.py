from pymongo.database import Database
from pymongo.errors import DuplicateKeyError

from app.db.serialize import doc_to_dict, docs_to_dicts, prepare_insert, prepare_update
from app.schemas.component_definition import ComponentDefinitionCreate, ComponentDefinitionRead


def list_component_definitions(db: Database) -> list[ComponentDefinitionRead]:
    docs = list(
        db.component_definitions.find().sort([("category", 1), ("label", 1)])
    )
    return [ComponentDefinitionRead.model_validate(doc) for doc in docs_to_dicts(docs)]


def get_component_definition_by_type(db: Database, component_type: str) -> ComponentDefinitionRead | None:
    doc = db.component_definitions.find_one({"type": component_type})
    parsed = doc_to_dict(doc)
    return ComponentDefinitionRead.model_validate(parsed) if parsed else None


def create_component_definition(
    db: Database, data: ComponentDefinitionCreate
) -> ComponentDefinitionRead:
    payload = prepare_insert(
        {
            "type": data.type,
            "label": data.label,
            "icon": data.icon,
            "category": data.category,
            "default_props": data.default_props,
            "property_schema": [field.model_dump() for field in data.property_schema],
            "is_container": data.is_container,
            "is_input": data.is_input,
            "data_type": data.data_type,
        }
    )
    try:
        result = db.component_definitions.insert_one(payload)
    except DuplicateKeyError as exc:
        raise exc

    doc = db.component_definitions.find_one({"_id": result.inserted_id})
    return ComponentDefinitionRead.model_validate(doc_to_dict(doc))


def group_definitions_by_category(
    definitions: list[ComponentDefinitionRead],
) -> dict[str, list[ComponentDefinitionRead]]:
    grouped: dict[str, list[ComponentDefinitionRead]] = {}
    for definition in definitions:
        grouped.setdefault(definition.category, []).append(definition)
    return grouped


def get_input_type_data_types(db: Database) -> dict[str, str]:
    """Maps component_type -> data_type for every component marked is_input.

    Used by page_data_schema_service to know which nodes in a page's layout
    tree capture data, and what Mongo field type to use for each.
    """
    docs = db.component_definitions.find(
        {"is_input": True}, {"type": 1, "data_type": 1}
    )
    return {doc["type"]: doc.get("data_type", "string") for doc in docs}
