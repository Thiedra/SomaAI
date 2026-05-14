from django.urls import path
from .views import GameScoreView

urlpatterns = [
    path("score/", GameScoreView.as_view(), name="game-score"),
]
