# Django foundation

**Model**:
A Django ORM class representing a database table and its rows.
_Avoid_: Entity, table (when meaning the ORM class)

**Model instance**:
A single row of a model, loaded from or about to be written to the database.
_Avoid_: Model (when an instance is meant), record, object (unqualified)

**Queryset**:
A lazy, chainable collection of model instances produced by a model's manager.
_Avoid_: Result set, query result, rows

**Lookup**:
A Django ORM filter expression passed to `queryset.filter()` — field name plus optional lookup type (e.g. `name__icontains`).
_Avoid_: Filter (when the Django ORM mechanism is meant), predicate

**Manager**:
The interface on a model for obtaining querysets — typically the default `objects` manager.
_Avoid_: Repository, DAO

**Primary key**:
The unique identifier for a model instance, exposed as `pk` or `id` on the instance.
_Avoid_: ID (ambiguous with global object ID), key
