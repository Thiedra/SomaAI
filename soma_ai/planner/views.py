"""
planner/views.py

API views for the Study Planner calendar event sync.

The frontend previously stored all planner events in localStorage under
the key "soma_cal_events". These views replace that with a proper backend
sync so events persist across devices and browser sessions.

Available endpoints (all require IsStudent permission):
  GET    /api/v1/planner/events/           — list all events for the student
  POST   /api/v1/planner/events/           — create a new event
  PUT    /api/v1/planner/events/<id>/      — update an event (partial)
  DELETE /api/v1/planner/events/<id>/      — permanently delete an event

Optional query parameter:
  ?date=YYYY-MM-DD  — filter events by a specific date (used by the
                      frontend day-view to load events for the selected day)
"""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from core.permissions import IsStudent
from .models import CalendarEvent
from .serializers import CalendarEventSerializer, CalendarEventUpdateSerializer


class CalendarEventListCreateView(APIView):
    """
    Handles listing and creating calendar events for the authenticated student.

    GET  — Returns all events belonging to the student, ordered by date.
           Supports optional ?date=YYYY-MM-DD filter for day-view rendering.

    POST — Creates a new calendar event. The student field is set
           automatically from request.user — the client never sends it.
    """
    permission_classes = [IsStudent]

    @extend_schema(
        summary="List calendar events",
        description=(
            "Returns all calendar events for the authenticated student, ordered by date. "
            "Filter by a specific date using the optional ?date=YYYY-MM-DD query parameter."
        ),
        tags=["Planner"],
        responses={200: CalendarEventSerializer(many=True)},
    )
    def get(self, request):
        events = CalendarEvent.objects.filter(student=request.user)

        # apply optional date filter — used by the frontend day-view
        date_filter = request.query_params.get("date")
        if date_filter:
            events = events.filter(date=date_filter)

        return Response(CalendarEventSerializer(events, many=True).data)

    @extend_schema(
        summary="Create a calendar event",
        description=(
            "Creates a new calendar event for the authenticated student. "
            "The student field is set server-side — do not include it in the request body."
        ),
        tags=["Planner"],
        request=CalendarEventSerializer,
        responses={
            201: CalendarEventSerializer,
            400: OpenApiResponse(description="Validation error — check field values"),
        },
    )
    def post(self, request):
        serializer = CalendarEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # inject the authenticated student — never trust the client to send this
        event = serializer.save(student=request.user)

        return Response(
            CalendarEventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )


class CalendarEventDetailView(APIView):
    """
    Handles updating and deleting a single calendar event.

    PUT    — Partially updates the event. Only the fields included in the
             request body are changed. Commonly used for:
               - Marking an event done: { done: true }
               - Adding a teacher mark: { mark: 85 }
               - Rescheduling: { date: "2025-07-01" }

    DELETE — Permanently removes the event from the database.

    Both operations are restricted to the event's owner. Attempting to
    modify another student's event returns 404 (not 403) to avoid
    leaking the existence of other students' data.
    """
    permission_classes = [IsStudent]

    def _get_event(self, event_id, student):
        """
        Fetch a CalendarEvent by ID scoped to the requesting student.
        Returns None if the event does not exist or belongs to another student.
        """
        try:
            return CalendarEvent.objects.get(id=event_id, student=student)
        except CalendarEvent.DoesNotExist:
            return None

    @extend_schema(
        summary="Update a calendar event",
        description=(
            "Partially updates a calendar event. All fields are optional — "
            "only the fields included in the request body will be changed. "
            "Common use cases: marking done, adding a mark, rescheduling."
        ),
        tags=["Planner"],
        request=CalendarEventUpdateSerializer,
        responses={
            200: CalendarEventSerializer,
            400: OpenApiResponse(description="Validation error"),
            404: OpenApiResponse(description="Event not found or does not belong to this student"),
        },
    )
    def put(self, request, event_id):
        event = self._get_event(event_id, request.user)
        if not event:
            return Response(
                {"error": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = CalendarEventUpdateSerializer(
            event,
            data=request.data,
            partial=True,   # allow sending only the changed fields
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # return the full updated event using the read serializer
        return Response(CalendarEventSerializer(event).data)

    @extend_schema(
        summary="Delete a calendar event",
        description="Permanently deletes a calendar event owned by the authenticated student.",
        tags=["Planner"],
        responses={
            200: OpenApiResponse(description="Event deleted successfully"),
            404: OpenApiResponse(description="Event not found or does not belong to this student"),
        },
    )
    def delete(self, request, event_id):
        event = self._get_event(event_id, request.user)
        if not event:
            return Response(
                {"error": "Event not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        event.delete()
        return Response({"success": True})
