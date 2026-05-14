"""
library/views.py
Read-only views for Videos and Books.
Both support query param filtering as required by the frontend.
"""
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema

from .models import Video, Book
from .serializers import VideoSerializer, BookSerializer


class VideoListView(APIView):
    """
    GET /api/v1/videos/
    Returns videos filtered by optional ?subject= and ?level= params.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List videos",
        description="Filter with ?subject=Math and/or ?level=P6.",
        tags=["Library"],
        responses={200: VideoSerializer(many=True)},
    )
    def get(self, request):
        videos = Video.objects.all()

        subject = request.query_params.get("subject")
        level   = request.query_params.get("level")

        if subject:
            videos = videos.filter(subject=subject)
        if level:
            videos = videos.filter(level=level)

        return Response(VideoSerializer(videos, many=True).data)


class BookListView(APIView):
    """
    GET /api/v1/library/
    Returns books filtered by optional ?grade=, ?type=, ?subject= params.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List library books",
        description="Filter with ?grade=P6, ?type=PB, and/or ?subject=Math.",
        tags=["Library"],
        responses={200: BookSerializer(many=True)},
    )
    def get(self, request):
        books = Book.objects.all()

        grade   = request.query_params.get("grade")
        type_   = request.query_params.get("type")
        subject = request.query_params.get("subject")

        if grade:
            books = books.filter(grade=grade)
        if type_:
            books = books.filter(book_type=type_)
        if subject:
            books = books.filter(subject__icontains=subject)

        return Response(BookSerializer(books, many=True).data)
