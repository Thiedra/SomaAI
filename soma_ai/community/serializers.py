"""
community/serializers.py

Serializers for the Community feed endpoints.

CommunityPostSerializer       — used for GET /community/posts/ (list).
                                 Returns the full post shape the frontend expects.

CommunityPostCreateSerializer — used for POST /community/posts/ (create).
                                 Accepts only the `msg` field as per the
                                 frontend contract: { msg: string }.

Frontend Post shape:
    { id, user, msg, likes, createdAt }
"""
from rest_framework import serializers
from .models import CommunityPost


class CommunityPostSerializer(serializers.ModelSerializer):
    """
    Read serializer for a community post.

    Maps model fields to the exact frontend Post shape:
        user      — author's display name (full_name), not their UUID
        msg       — the post content body
        likes     — total like count derived from PostLike records
        createdAt — ISO 8601 timestamp

    `author` (FK) is intentionally excluded from the output to avoid
    exposing internal user IDs in the public feed.
    """
    user      = serializers.CharField(
        source="author.full_name",
        read_only=True,
        help_text="Display name of the post author.",
    )
    msg       = serializers.CharField(
        source="content",
        read_only=True,
        help_text="The post body text.",
    )
    likes     = serializers.IntegerField(
        source="like_count",
        read_only=True,
        help_text="Total number of likes on this post.",
    )
    createdAt = serializers.DateTimeField(
        source="created_at",
        read_only=True,
        help_text="ISO 8601 timestamp of when the post was created.",
    )

    class Meta:
        model  = CommunityPost
        fields = ["id", "user", "msg", "likes", "createdAt"]


class CommunityPostCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new community post.

    The frontend sends only { msg: string } — the author is injected
    server-side from request.user so the client cannot spoof authorship.
    """
    msg = serializers.CharField(
        max_length=1000,
        help_text="The post body — maximum 1000 characters.",
    )

    def validate_msg(self, value):
        """Reject empty or whitespace-only messages."""
        if not value.strip():
            raise serializers.ValidationError(
                "Post message cannot be empty."
            )
        return value.strip()
