# Django foundation

## Model

A Django ORM class representing a database table and its rows.

Avoid: Entity, table (when meaning the ORM class)

## Model instance

A single row of a model, loaded from or about to be written to the database.

Avoid: Model (when an instance is meant), record, object (unqualified)

## Queryset

A lazy, chainable collection of model instances produced by a model's manager.

Avoid: Result set, query result, rows

## Lookup

A Django ORM filter expression passed to `queryset.filter()`. Field name plus optional
lookup type (e.g. `name__icontains`).

Avoid: Filter (when the Django ORM mechanism is meant), predicate

## Manager

The interface on a model for obtaining querysets. Typically the default `objects` manager.

Avoid: Repository, DAO

## Primary key

The unique identifier for a model instance, exposed as `pk` or `id` on the instance.

Avoid: ID (ambiguous with global object ID), key
