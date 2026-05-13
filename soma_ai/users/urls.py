"""
users/urls.py
URL routing for authentication and user management.
All routes are prefixed with /api/v1/auth/ from the root urls.py.
"""
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterView, LoginView, LogoutView, MeView,
    StudentStatsUpdateView, ChangePasswordView,
    UserDetailView, EnrollStudentView, MyStudentsView, StudentDetailView,
)

urlpatterns = [
    # --- Public ---
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # --- Authenticated ---
    path("me/", MeView.as_view(), name="me"),
    path("me/stats/", StudentStatsUpdateView.as_view(), name="me-stats"),
    path("password/change/", ChangePasswordView.as_view(), name="change-password"),
    path("users/<uuid:user_id>/", UserDetailView.as_view(), name="user-detail"),

    # --- Teacher only ---
    path("teachers/enroll-student/", EnrollStudentView.as_view(), name="enroll-student"),
    path("teachers/my-students/", MyStudentsView.as_view(), name="my-students"),
    path("teachers/students/<uuid:user_id>/", StudentDetailView.as_view(), name="student-detail"),
]
