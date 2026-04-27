"""JSON serialization helpers for datetime/date objects."""

from datetime import date, datetime


def serialize_value(obj):
    """Convert datetime/date objects to ISO 8601 strings, recursively."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, dict):
        return {k: serialize_value(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [serialize_value(item) for item in obj]
    return obj
