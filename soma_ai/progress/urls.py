from django.urls import path
from .views import (
    MyProgressView, MyProgressGraphView, MyMasteryView,
    MyProgressFrontendView, StudentProgressView,
    AlertListView, AlertMarkReadView, MotivationView,
)

urlpatterns = [
    # --- Student ---
    path("me/", MyProgressView.as_view(), name="my-progress"),
    path("me/mastery/", MyMasteryView.as_view(), name="my-mastery"),
    path("me/weekly/", MyProgressFrontendView.as_view(), name="my-progress-weekly"),
    path("me/graph/", MyProgressGraphView.as_view(), name="my-progress-graph"),
    path("me/motivation/", MotivationView.as_view(), name="motivation"),

    # --- Teacher ---
    path("students/<uuid:student_id>/", StudentProgressView.as_view(), name="student-progress"),
    path("alerts/", AlertListView.as_view(), name="alert-list"),
    path("alerts/<uuid:alert_id>/read/", AlertMarkReadView.as_view(), name="alert-read"),
]
