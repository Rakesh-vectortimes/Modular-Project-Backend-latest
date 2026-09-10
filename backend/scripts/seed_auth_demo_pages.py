"""Seed demo Sign up + Login pages with mapped field keys and auth button actions.

Usage (from backend/):
    python -m scripts.seed_auth_demo_pages

Requires MongoDB and at least one software project in the database.
"""

from __future__ import annotations

from app.db.mongo import get_database, init_indexes, new_object_id
from app.schemas.layout import LayoutNodeWrite, PageSettings, PositionSchema
from app.schemas.page import PageCreate
from app.services import page_layout_service, page_service


def _pos(x: float, y: float, w: float, h: float) -> PositionSchema:
    return PositionSchema(x=x, y=y, w=w, h=h)


def _text_input(
    *,
    label: str,
    field_key: str,
    order: int,
    placeholder: str = "",
    required: bool = True,
) -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="text_input",
        order=order,
        position=_pos(0, 0, 280, 62),
        props={
            "label": label,
            "placeholder": placeholder or f"Enter {label.lower()}…",
            "required": required,
            "unique": False,
            "defaultValue": "",
            "fieldKey": field_key,
        },
        children=[],
    )


def _email(order: int) -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="email_input",
        order=order,
        position=_pos(0, 0, 280, 62),
        props={
            "label": "Email",
            "placeholder": "you@example.com",
            "required": True,
            "unique": False,
            "defaultValue": "",
            "fieldKey": "email",
        },
        children=[],
    )


def _password(order: int, label: str = "Password") -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="password_input",
        order=order,
        position=_pos(0, 0, 280, 62),
        props={
            "label": label,
            "placeholder": "At least 8 characters",
            "required": True,
            "showToggle": True,
            "fieldKey": "password",
        },
        children=[],
    )


def _heading(content: str, order: int) -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="heading",
        order=order,
        position=_pos(0, 0, 320, 40),
        props={
            "content": content,
            "binding": "",
            "level": "h2",
            "align": "center",
            "color": "#111827",
        },
        children=[],
    )


def _button(label: str, order: int, action: dict) -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="button",
        order=order,
        position=_pos(0, 0, 280, 40),
        props={
            "label": label,
            "variant": "primary",
            "action": action,
        },
        children=[],
    )


def _link(label: str, order: int, target_page_id: str) -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="link_button",
        order=order,
        position=_pos(0, 0, 220, 28),
        props={
            "label": label,
            "action": {"actionType": "navigate", "targetPageId": target_page_id},
        },
        children=[],
    )


def _section(label: str, children: list[LayoutNodeWrite], *, h: float) -> LayoutNodeWrite:
    return LayoutNodeWrite(
        id=str(new_object_id()),
        component_type="section",
        order=0,
        position=_pos(420, 80, 440, h),
        props={
            "label": label,
            "backgroundColor": "#ffffff",
            "padding": 28,
            "direction": "column",
            "gap": 12,
        },
        children=children,
    )


def build_signup_page(login_page_id: str) -> list[LayoutNodeWrite]:
    children = [
        _heading("Create your account", 0),
        _text_input(label="First name", field_key="firstName", order=1),
        _text_input(label="Last name", field_key="lastName", order=2),
        _email(3),
        _password(4),
        _text_input(label="Phone", field_key="phone", order=5, placeholder="+1 555 0100"),
        _text_input(label="Address", field_key="address", order=6),
        _text_input(label="Pincode", field_key="pincode", order=7),
        _button(
            "Sign up",
            8,
            {
                "actionType": "signup",
                "targetPageId": login_page_id,
                "successMessage": "Account created! You can log in now.",
            },
        ),
        _link("Already have an account? Log in", 9, login_page_id),
    ]
    return [_section("Sign up form", children, h=720)]


def build_login_page(signup_page_id: str) -> list[LayoutNodeWrite]:
    children = [
        _heading("Welcome back", 0),
        _email(1),
        _password(2),
        _button(
            "Log in",
            3,
            {
                "actionType": "login",
                "emailFieldKey": "email",
                "passwordFieldKey": "password",
                "successMessage": "Logged in successfully!",
            },
        ),
        _link("Need an account? Sign up", 4, signup_page_id),
    ]
    return [_section("Login form", children, h=380)]


def _find_or_create_page(db, *, organization_id: str, software_id: str, name: str, is_default: bool):
    existing = db.pages.find_one({"software_id": software_id, "name": name})
    if existing:
        return str(existing["_id"]), False

    page = page_service.create_page(
        db,
        organization_id=organization_id,
        data=PageCreate(name=name, is_default=is_default, software_id=software_id),
    )
    return page.id, True


def seed_auth_demo_pages() -> None:
    db = get_database()
    init_indexes()

    software = db.software.find_one(sort=[("created_at", -1)])
    if not software:
        print("No software project found. Create one in the App Builder first, then re-run.")
        return

    software_id = str(software["_id"])
    organization_id = software["organization_id"]
    print(f"Using software: {software.get('name', software_id)} ({software_id})")

    login_id, login_new = _find_or_create_page(
        db,
        organization_id=organization_id,
        software_id=software_id,
        name="login",
        is_default=True,
    )
    signup_id, signup_new = _find_or_create_page(
        db,
        organization_id=organization_id,
        software_id=software_id,
        name="signup",
        is_default=False,
    )

    settings = PageSettings(
        backgroundColor="#eef2f7",
        viewportWidth=1280,
        viewportHeight=800,
    )

    page_layout_service.replace_page_layout(
        db, signup_id, build_signup_page(login_id), settings=settings
    )
    page_layout_service.replace_page_layout(
        db, login_id, build_login_page(signup_id), settings=settings
    )

    page_service.set_default_page(db, login_id, organization_id)

    print(
        f"{'Created' if signup_new else 'Updated'} signup page: {signup_id}\n"
        f"{'Created' if login_new else 'Updated'} login page: {login_id} (default)\n"
        f"Preview signup: /run/{software_id}/{signup_id}\n"
        f"Preview login:  /run/{software_id}/{login_id}\n"
        f"Published (default login): /p/{software_id}"
    )


if __name__ == "__main__":
    seed_auth_demo_pages()
