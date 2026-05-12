"""
progress/urls.py
URL routing for student progress tracking and teacher endpoints.
"""
from django.urls import path
from .views import (
    MyProgressView, MyProgressGraphView,
    StudentProgressView, AlertListView,
    AlertMarkReadView, MotivationView,
)

urlpatterns = [
    # --- Student endpoints ---
    path("me/", MyProgressView.as_view(), name="my-progress"),
    path("me/graph/", MyProgressGraphView.as_view(), name="my-progress-graph"),
    path("me/motivation/", MotivationView.as_view(), name="motivation"),

    # --- Teacher endpoints ---
    path("students/<uuid:student_id>/", StudentProgressView.as_view(), name="student-progress"),
]
