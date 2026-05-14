"""
homework/urls.py

URL routing for the Homework and Assignment features.

Student routes  (prefixed /api/v1/homework/):
  GET  /api/v1/homework/                  — list student's homework
  PUT  /api/v1/homework/<id>/complete/    — mark homework as done

Teacher routes  (prefixed /api/v1/assignments/):
  GET    /api/v1/assignments/             — list teacher's assignments
  POST   /api/v1/assignments/             — create assignment + distribute homework
  DELETE /api/v1/assignments/<id>/        — delete assignment
  PUT    /api/v1/assignments/<id>/submit/ — record a student's submission
"""
from django.urls import path
from .views import (
    HomeworkListView,
    HomeworkCompleteView,
    AssignmentListCreateView,
    AssignmentDeleteView,
    AssignmentSubmitView,
)

# Student homework routes
homework_urlpatterns = [
    path(
        "",
        HomeworkListView.as_view(),
        name="homework-list",
    ),
    path(
        "<uuid:homework_id>/complete/",
        HomeworkCompleteView.as_view(),
        name="homework-complete",
    ),
]

# Teacher assignment routes
assignment_urlpatterns = [
    path(
        "",
        AssignmentListCreateView.as_view(),
        name="assignment-list-create",
    ),
    path(
        "<uuid:assignment_id>/",
        AssignmentDeleteView.as_view(),
        name="assignment-delete",
    ),
    path(
        "<uuid:assignment_id>/submit/",
        AssignmentSubmitView.as_view(),
        name="assignment-submit",
    ),
]
