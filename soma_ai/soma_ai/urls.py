"""
soma_ai/urls.py
Root URL configuration for Soma AI.
"""
from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView,
)
from homework.urls import homework_urlpatterns, assignment_urlpatterns
from library.urls import book_urlpatterns
from django.http import HttpResponse


urlpatterns = [
    path("", lambda request: HttpResponse("ok"), name="healthcheck"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # auth
    path("api/v1/auth/", include("users.urls")),

    # student features
    path("api/v1/notes/", include("simplifier.urls")),
    path("api/v1/quizzes/", include("quizzes.urls")),
    path("api/v1/progress/", include("progress.urls")),
    path("api/v1/planner/", include("planner.urls")),
    path("api/v1/career/", include("career.urls")),
    path("api/v1/homework/", include((homework_urlpatterns, "homework"))),
    path("api/v1/community/", include("community.urls")),  
    path("api/v1/videos/", include("library.urls")),                 
    path("api/v1/library/", include((book_urlpatterns, "library"))),    

    # teacher features
    path("api/v1/teacher/", include("dashboard.urls")),
    path("api/v1/assignments/", include((assignment_urlpatterns, "assignments"))),
    # Ai features
    path("api/v1/ai/", include("ai_proxy.urls")),
    # Games
    path("api/v1/games/", include("games.urls")),


]
