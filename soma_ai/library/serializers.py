
from rest_framework import serializers
from .models import Video, Book


class VideoSerializer(serializers.ModelSerializer):
    """
    Frontend Video shape:
    { id, title, subject, level, duration, teacherRecommended }
    """
    teacherRecommended = serializers.BooleanField(source="teacher_recommended")

    class Meta:
        model = Video
        fields = ["id", "youtube_id", "title", "subject", "level", "duration", "teacherRecommended"]


class BookSerializer(serializers.ModelSerializer):
    """
    Frontend Book shape:
    { id, title, file, grade, type, subject }
    `file` maps to file_url, `type` maps to book_type.
    """
    file = serializers.CharField(source="file_url")
    type = serializers.CharField(source="book_type")

    class Meta:
        model = Book
        fields = ["id", "title", "file", "grade", "type", "subject"]
