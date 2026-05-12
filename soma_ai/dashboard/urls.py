"""
dashboard/urls.py
URL routing for teacher dashboard endpoints.
All routes are prefixed with /api/v1/dashboard/ from the root urls.py.
"""
from django.urls import path
from .views import (
    DashboardOverviewView,
    DashboardStudentListView,
    DashboardStudentDetailView,
    DashboardStrugglingView,
)

urlpatterns = [
    # aggregated class overview
    path("overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),

    # full student list with sorting
    path("students/", DashboardStudentListView.as_view(), name="dashboard-students"),

    # single student full details
    path("students/<uuid:student_id>/full/", DashboardStudentDetailView.as_view(), name="dashboard-student-detail"),

    # only struggling students
    path("struggling/", DashboardStrugglingView.as_view(), name="dashboard-struggling"),
]
