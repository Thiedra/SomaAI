# games/serializers.py
from rest_framework import serializers

class GameScoreSerializer(serializers.Serializer):
    gameId  = serializers.CharField()
    score   = serializers.IntegerField()
    # studentId is accepted but ignored — student is set from request.user
    studentId = serializers.UUIDField(required=False)
    def validate_score(self, value):
        if value < 0:
            raise serializers.ValidationError("Score must be a non-negative integer.")
        return value