"""
quizzes/urls.py
URL routing for quiz generation, retrieval, attempts, and results.
All routes are prefixed with /api/v1/quizzes/ from the root urls.py.
"""
from django.urls import path
from .views import (
    GenerateQuizView, QuizListView, QuizDetailView,
    AttemptQuizView, QuizResultsView,
)

urlpatterns = [
    # quiz generation and listing
    path("generate/", GenerateQuizView.as_view(), name="quiz-generate"),
    path("", QuizListView.as_view(), name="quiz-list"),

    # single quiz operations
    path("<uuid:quiz_id>/", QuizDetailView.as_view(), name="quiz-detail"),
    path("<uuid:quiz_id>/attempt/", AttemptQuizView.as_view(), name="quiz-attempt"),
    path("<uuid:quiz_id>/results/", QuizResultsView.as_view(), name="quiz-results"),
]
