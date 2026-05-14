"""
planner/urls.py

URL routing for the Study Planner feature.
All routes are prefixed with /api/v1/planner/ from the root urls.py.

Route summary:
  GET  POST  /api/v1/planner/events/          → CalendarEventListCreateView
  PUT  DELETE /api/v1/planner/events/<id>/    → CalendarEventDetailView
"""
from django.urls import path
from .views import CalendarEventListCreateView, CalendarEventDetailView

urlpatterns = [
    # list all events / create a new event
    path(
        "events/",
        CalendarEventListCreateView.as_view(),
        name="planner-events",
    ),
    # update or delete a single event by UUID
    path(
        "events/<uuid:event_id>/",
        CalendarEventDetailView.as_view(),
        name="planner-event-detail",
    ),
]
