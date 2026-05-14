# games/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import GameScore
from .serializers import GameScoreSerializer


class GameScoreView(APIView):
    """
    POST /api/v1/games/score/
    Records a game score and awards XP to the student.
    Body: { gameId, score, studentId }  →  { success: true }
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Submit game score",
        description="Records a game score and awards XP. Body: { gameId, score }.",
        tags=["Games"],
        request=GameScoreSerializer,
        responses={
            201: OpenApiResponse(description="{ success: true }"),
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def post(self, request):
        serializer = GameScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        GameScore.objects.create(
            student=request.user,
            game_id=serializer.validated_data["gameId"],
            score=serializer.validated_data["score"],
        )

        # award XP based on score — 1 XP per point, max 100 XP per game
        xp_earned = min(serializer.validated_data["score"], 100)
        if xp_earned > 0 and request.user.is_student:
            request.user.xp += xp_earned
            request.user.update_level()
            request.user.save(update_fields=["xp", "level"])

        return Response({"success": True}, status=status.HTTP_201_CREATED)
