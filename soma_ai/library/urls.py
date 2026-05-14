"""
library/urls.py
Routes for Videos and Books.
"""
from django.urls import path
from .views import VideoListView, BookListView

urlpatterns = [
    path("", VideoListView.as_view(), name="video-list"),
]

book_urlpatterns = [
    path("", BookListView.as_view(), name="book-list"),
]
