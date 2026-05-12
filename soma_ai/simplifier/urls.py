"""
simplifier/urls.py
URL routing for note management, AI simplification, and TTS.
All routes are prefixed with /api/v1/notes/ from the root urls.py.
"""
from django.urls import path
from .views import (
    NoteListCreateView, NoteDetailView,
    SimplifyNoteView, SimplifiedNoteView,
    TTSRequestView, TTSStatusView,
)

urlpatterns = [
    path("", NoteListCreateView.as_view(), name="note-list-create"),
    path("<uuid:note_id>/", NoteDetailView.as_view(), name="note-detail"),
    path("<uuid:note_id>/simplify/", SimplifyNoteView.as_view(), name="note-simplify"),
    path("<uuid:note_id>/simplified/", SimplifiedNoteView.as_view(), name="note-simplified"),
    path("<uuid:note_id>/tts/", TTSRequestView.as_view(), name="note-tts"),
    path("<uuid:note_id>/tts/status/", TTSStatusView.as_view(), name="note-tts-status"),
]
