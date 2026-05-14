"""
community/models.py

Models for the Soma AI Community feature.

CommunityPost — A public message posted by a student or teacher to the
                shared community feed. Visible to all authenticated users.

PostLike      — Records a single user's like on a post. Using a separate
                model (rather than a plain integer counter) prevents the
                same user from liking a post more than once and allows
                the frontend to show whether the current user has liked
                a given post.

Frontend Post shape:
    { id, user, msg, likes, createdAt }
"""
import uuid
from django.db import models
from django.conf import settings


class CommunityPost(models.Model):
    """
    A single post on the community feed.

    Any authenticated user (student or teacher) can create a post.
    The `likes` count is derived from the related PostLike records —
    it is never stored as a plain integer to avoid race conditions
    when multiple users like a post simultaneously.

    Frontend field mapping:
        Frontend key  →  Model field
        ────────────────────────────
        user          →  author.full_name  (read-only display name)
        msg           →  content
        likes         →  like_count (computed via PostLike)
        createdAt     →  created_at
    """
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="community_posts",
        verbose_name="Author",
        help_text="The user who created this post.",
    )
    content = models.TextField(
        verbose_name="Message",
        help_text="The post body — maps to the frontend 'msg' field.",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Created At",
    )

    class Meta:
        verbose_name = "Community Post"
        verbose_name_plural = "Community Posts"
        ordering = ["-created_at"]   # newest posts appear first

    def __str__(self):
        return f"{self.author.full_name}: {self.content[:60]}"

    @property
    def like_count(self):
        """Return the total number of likes for this post."""
        return self.likes.count()


class PostLike(models.Model):
    """
    Records a single like from one user on one post.

    The unique_together constraint ensures a user can only like
    a post once. Attempting to like again returns the current
    like count without creating a duplicate record.
    """
    post = models.ForeignKey( CommunityPost,on_delete=models.CASCADE, related_name="likes",
        verbose_name="Post",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="post_likes",
        verbose_name="User",
    )
    liked_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Liked At",
    )

    class Meta:
        verbose_name = "Post Like"
        verbose_name_plural = "Post Likes"
        unique_together = ("post", "user")   # one like per user per post

    def __str__(self):
        return f"{self.user.full_name} liked '{self.post.content[:40]}'"
