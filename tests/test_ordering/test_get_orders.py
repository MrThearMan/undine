from __future__ import annotations

from example_project.app.models import Project, ServiceRequest, Task
from undine.ordering import get_orders_for_model, get_orders_for_models


def test_get_orders_for_model() -> None:
    fields = get_orders_for_model(Task)
    assert sorted(fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "created_at",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "name",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]


def test_get_orders_for_model__exclude() -> None:
    fields = get_orders_for_model(Task, exclude=["name"])
    assert sorted(fields) == [
        "acceptancecriteria",
        "assignees",
        "attachment",
        "check_time",
        "comments",
        "contact_email",
        "created_at",
        "demo_url",
        "done",
        "due_by",
        "external_uuid",
        "extra_data",
        "image",
        "objective",
        "pk",
        "points",
        "progress",
        "project",
        "related_tasks",
        "reports",
        "request",
        "result",
        "steps",
        "type",
        "worked_hours",
    ]


def test_get_orders_for_models() -> None:
    orders = get_orders_for_models((Task, Project))

    # Both Task and Project have 'name', so it should be included.
    assert "name" in orders

    # Task-specific fields should not be included.
    assert "type" not in orders
    assert "done" not in orders


def test_get_orders_for_models__exclude_pk() -> None:
    orders = get_orders_for_models((Task, Project), exclude=["pk"])

    # pk should be excluded.
    assert "pk" not in orders
    # name should still be present.
    assert "name" in orders


def test_get_orders_for_models__incompatible_field_types_excluded() -> None:
    # Only fields with the same graphql type across all models should be included.
    orders = get_orders_for_models((Task, Project))

    # Ensure only common, type-compatible fields are included.
    assert isinstance(orders, dict)


def test_get_orders_for_models__mismatched_field_types_skipped() -> None:
    # Task.created_at is DateTimeField, ServiceRequest.created_at is DateField.
    # created_at will be in common_fields but with different types, so it should be excluded.
    orders = get_orders_for_models((Task, ServiceRequest))
    assert "created_at" not in orders


def test_get_orders_for_models__exclude_pk_field() -> None:
    # When the resolved field_name is "pk" (primary key), it should be excluded.
    orders = get_orders_for_models((Task, Project), exclude=["pk"])
    assert "pk" not in orders
