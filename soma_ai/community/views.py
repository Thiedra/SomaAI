"""
community/views.py

API views for the Community feed feature.

Any authenticated user (student or teacher) can read and post to the
community feed. Liking a post is idempotent — liking an already-liked
post simply returns the current like count without creating a duplicate.

Available endpoints:
  GET  /api/v1/community/posts/           — list all posts (newest first)
  POST /api/v1/community/posts/           — create a new post
  POST /api/v1/community/posts/<id>/like/ — toggle a like on a post
"""
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from .models import CommunityPost, PostLike
from .serializers import CommunityPostSerializer, CommunityPostCreateSerializer


class CommunityPostListCreateView(APIView):
    """
    GET  — Returns all community posts ordered by newest first.
           Both students and teachers can read the feed.

    POST — Creates a new post. The author is set automatically from
           request.user — the client only sends { msg: string }.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="List community posts",
        description=(
            "Returns all community posts ordered by newest first. "
            "Accessible to all authenticated users (students and teachers)."
        ),
        tags=["Community"],
        responses={200: CommunityPostSerializer(many=True)},
    )
    def get(self, request):
        posts = CommunityPost.objects.select_related("author").prefetch_related("likes")
        return Response(CommunityPostSerializer(posts, many=True).data)

    @extend_schema(
        summary="Create a community post",
        description=(
            "Creates a new post on the community feed. "
            "Send only { msg: string } — the author is set from the authenticated user."
        ),
        tags=["Community"],
        request=CommunityPostCreateSerializer,
        responses={
            201: CommunityPostSerializer,
            400: OpenApiResponse(description="Validation error — message cannot be empty"),
        },
    )
    def post(self, request):
        serializer = CommunityPostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        post = CommunityPost.objects.create(
            author=request.user,
            content=serializer.validated_data["msg"],
        )

        return Response(
            CommunityPostSerializer(post).data,
            status=status.HTTP_201_CREATED,
        )


class CommunityPostLikeView(APIView):
    """
    POST /api/v1/community/posts/<id>/like/

    Toggles a like on a post for the authenticated user.

    - If the user has NOT liked the post → creates a PostLike record.
    - If the user HAS already liked the post → removes the PostLike record
      (unlike behaviour, consistent with modern social platforms).

    Returns { likes: <updated_count> } as specified by the frontend contract.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Like or unlike a community post",
        description=(
            "Toggles a like on the specified post. "
            "Liking an already-liked post removes the like (unlike). "
            "Returns the updated like count: { likes: number }."
        ),
        tags=["Community"],
        responses={
            200: OpenApiResponse(description="{ likes: number }"),
            404: OpenApiResponse(description="Post not found"),
        },
    )
    def post(self, request, post_id):
        try:
            post = CommunityPost.objects.prefetch_related("likes").get(id=post_id)
        except CommunityPost.DoesNotExist:
            return Response(
                {"error": "Post not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # get_or_create returns (instance, created_bool)
        # if created=False the like already exists — remove it (unlike)
        like, created = PostLike.objects.get_or_create(
            post=post,
            user=request.user,
        )

        if not created:
            # user already liked this post — remove the like
            like.delete()

        return Response({"likes": post.like_count})
