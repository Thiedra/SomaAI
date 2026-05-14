from django.urls import path
from .views import (
    AITutorView,
    AISimplifyView,
    AIQuizStartView,
    AIQuizAnswerView,
    AICareerView,
)

urlpatterns = [
    path("tutor/", AITutorView.as_view(), name="ai-tutor"),
    path("simplify/", AISimplifyView.as_view(), name="ai-simplify"),
    path("quiz/start/", AIQuizStartView.as_view(), name="ai-quiz-start"),
    path("quiz/answer/", AIQuizAnswerView.as_view(), name="ai-quiz-answer"),
    path("career/", AICareerView.as_view(), name="ai-career"),
]
