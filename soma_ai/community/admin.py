"""
community/admin.py

Admin configuration for the Community feed models.

CommunityPost — view and moderate all posts on the community feed.
                Inline shows all likes on each post.

PostLike      — view all like records (useful for moderation audits).
"""
from django.contrib import admin
from .models import CommunityPost, PostLike


class PostLikeInline(admin.TabularInline):
    """
    Shows all users who liked a post directly on the post admin page.
    Read-only — likes are managed by users, not admins.
    """
    model         = PostLike
    extra         = 0
    readonly_fields = ["user", "liked_at"]
    fields        = ["user", "liked_at"]
    verbose_name  = "Like"
    verbose_name_plural = "Likes"
    can_delete    = False


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    """
    Admin view for community posts.
    Allows moderators to search, filter, and delete inappropriate posts.
    """
    list_display    = ["author", "content_preview", "like_count", "created_at"]
    list_filter     = ["created_at"]
    search_fields   = ["author__full_name", "author__soma_id", "content"]
    ordering        = ["-created_at"]
    readonly_fields = ["id", "created_at", "like_count"]
    inlines         = [PostLikeInline]

    fieldsets = (
        ("Post Content", {
            "fields": ("id", "author", "content")
        }),
        ("Metadata", {
            "fields": ("like_count", "created_at")
        }),
    )

    @admin.display(description="Message Preview")
    def content_preview(self, obj):
        """Show a truncated preview of the post content in the list view."""
        return obj.content[:80] + "..." if len(obj.content) > 80 else obj.content

    @admin.display(description="Likes")
    def like_count(self, obj):
        return obj.like_count


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    """Admin view for post likes — useful for moderation audits."""
    list_display  = ["user", "post", "liked_at"]
    list_filter   = ["liked_at"]
    search_fields = ["user__full_name", "user__soma_id"]
    readonly_fields = ["liked_at"]
