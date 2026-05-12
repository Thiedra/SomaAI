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

urlpatterns = [
    path("", RedirectView.as_view(url="/api/docs/"), name="home"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # app routes
    path("api/v1/auth/", include("users.urls")),
    path("api/v1/notes/", include("simplifier.urls")),
    path("api/v1/quizzes/", include("quizzes.urls")),
    path("api/v1/progress/", include("progress.urls")),
    path("api/v1/alerts/", include("progress.alert_urls")),
    path("api/v1/planner/", include("planner.urls")),   
    path("api/v1/career/", include("career.urls")),
    path("api/v1/dashboard/", include("dashboard.urls")),  

]
