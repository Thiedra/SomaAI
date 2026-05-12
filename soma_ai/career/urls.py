"""
career/urls.py
URL routing for career assessment and matching endpoints.
All routes are prefixed with /api/v1/career/ from the root urls.py.
"""
from django.urls import path
from .views import (
    CareerQuestionsView, CareerProfileView, CareerProfileRefreshView,
)

urlpatterns = [
    # get the 8 questions
    path("questions/", CareerQuestionsView.as_view(), name="career-questions"),

    # submit answers and get results
    path("profile/", CareerProfileView.as_view(), name="career-profile"),

    # re-run AI matching
    path("profile/refresh/", CareerProfileRefreshView.as_view(), name="career-refresh"),
]
