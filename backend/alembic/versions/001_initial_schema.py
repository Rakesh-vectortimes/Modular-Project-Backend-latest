"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-07-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "component_definitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(length=100), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("default_props", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("property_schema", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_container", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("type"),
    )
    op.create_index("ix_component_definitions_category", "component_definitions", ["category"])
    op.create_index("ix_component_definitions_type", "component_definitions", ["type"])

    op.create_table(
        "software",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("owner_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "pages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("software_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["software_id"], ["software.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pages_software_id", "pages", ["software_id"])
    op.create_index(
        "uq_pages_one_default_per_software",
        "pages",
        ["software_id"],
        unique=True,
        postgresql_where=sa.text("is_default = true"),
    )

    op.create_table(
        "page_components",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("page_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("component_type", sa.String(length=100), nullable=False),
        sa.Column("props", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("position", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["component_type"], ["component_definitions.type"]),
        sa.ForeignKeyConstraint(["page_id"], ["pages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["page_components.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_page_components_page_id", "page_components", ["page_id"])
    op.create_index("ix_page_components_parent_id", "page_components", ["parent_id"])


def downgrade() -> None:
    op.drop_index("ix_page_components_parent_id", table_name="page_components")
    op.drop_index("ix_page_components_page_id", table_name="page_components")
    op.drop_table("page_components")
    op.drop_index("uq_pages_one_default_per_software", table_name="pages")
    op.drop_index("ix_pages_software_id", table_name="pages")
    op.drop_table("pages")
    op.drop_table("software")
    op.drop_index("ix_component_definitions_type", table_name="component_definitions")
    op.drop_index("ix_component_definitions_category", table_name="component_definitions")
    op.drop_table("component_definitions")
