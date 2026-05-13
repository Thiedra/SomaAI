"""
dashboard/urls.py
"""
from django.urls import path
from .views import (
    TeacherMeView, TeacherStudentsView, TeacherStudentDetailView,
    TeacherReportsView, DashboardOverviewView, DashboardStudentListView,
    DashboardStudentDetailView, DashboardStrugglingView,
)

urlpatterns = [
    # --- Frontend-aligned teacher endpoints ---
    path("me/", TeacherMeView.as_view(), name="teacher-me"),
    path("students/", TeacherStudentsView.as_view(), name="teacher-students"),
    path("students/<uuid:student_id>/", TeacherStudentDetailView.as_view(), name="teacher-student-detail"),
    path("reports/", TeacherReportsView.as_view(), name="teacher-reports"),

    # --- Internal dashboard endpoints ---
    path("overview/", DashboardOverviewView.as_view(), name="dashboard-overview"),
    path("overview/students/", DashboardStudentListView.as_view(), name="dashboard-students"),
    path("overview/students/<uuid:student_id>/full/", DashboardStudentDetailView.as_view(), name="dashboard-student-detail"),
    path("struggling/", DashboardStrugglingView.as_view(), name="dashboard-struggling"),
]
