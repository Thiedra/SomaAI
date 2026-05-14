"""
planner/serializers.py

Serializers for the Study Planner calendar event endpoints.

CalendarEventSerializer       — used for GET (list) and POST (create).
CalendarEventUpdateSerializer — used for PUT (partial update). All fields
                                 are optional so the frontend can send only
                                 the changed fields (e.g. just { done: true }).

Frontend field mapping:
    Frontend key   →  Model field
    ─────────────────────────────
    dueNotified    →  due_notified
    (all others match 1:1)
"""
from rest_framework import serializers
from .models import CalendarEvent


def _validate_mark(value):
    """Reusable mark validator — ensures value is between 0 and 100."""
    if value is not None and not (0 <= value <= 100):
        raise serializers.ValidationError(
            "Mark must be an integer between 0 and 100."
        )
    return value


class CalendarEventSerializer(serializers.ModelSerializer):
    """
    Primary serializer for CalendarEvent.

    Used by:
      GET  /api/v1/planner/events/     — list all events
      POST /api/v1/planner/events/     — create a new event

    The `student` field is intentionally excluded — it is injected
    server-side from request.user so the client cannot spoof ownership.

    `dueNotified` uses camelCase to match the frontend CalEvent type.
    """
    dueNotified = serializers.BooleanField(
        source="due_notified",
        required=False,
        default=False,
        help_text="True once the frontend has shown a due-date notification.",
    )

    class Meta:
        model = CalendarEvent
        fields = [
            "id", "title", "date", "color",
            "type", "done", "mark", "dueNotified",
        ]
        read_only_fields = ["id"]

    def validate_mark(self, value):
        return _validate_mark(value)


class CalendarEventUpdateSerializer(serializers.ModelSerializer):
    """
    Partial update serializer for CalendarEvent.

    Used by:
      PUT /api/v1/planner/events/<id>/  — update any subset of fields

    All fields are optional — the frontend typically sends a single
    changed field (e.g. { done: true } when ticking off a task, or
    { mark: 85 } when a teacher grades an assignment).
    """
    dueNotified = serializers.BooleanField(
        source="due_notified",
        required=False,
        help_text="Set to true once the due-date notification has been shown.",
    )

    class Meta:
        model = CalendarEvent
        fields = [
            "title", "date", "color",
            "type", "done", "mark", "dueNotified",
        ]

    def validate_mark(self, value):
        return _validate_mark(value)
