"""
library/admin.py
Admin config for Videos and Books.
"""
from django.contrib import admin
from .models import Video, Book


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display  = ["title", "subject", "level", "duration", "teacher_recommended"]
    list_filter   = ["subject", "level", "teacher_recommended"]
    search_fields = ["title", "youtube_id"]
    ordering      = ["subject", "level"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display  = ["title", "grade", "book_type", "subject"]
    list_filter   = ["grade", "book_type", "subject"]
    search_fields = ["title"]
    ordering      = ["grade", "subject"]
