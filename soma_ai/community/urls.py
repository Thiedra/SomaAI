from django.urls import path
from .views import CommunityPostListCreateView, CommunityPostLikeView

urlpatterns = [
    # list all posts / create a new post
    path(
        "posts/",
        CommunityPostListCreateView.as_view(),
        name="community-posts",
    ),
    # like or unlike a specific post
    path(
        "posts/<uuid:post_id>/like/",
        CommunityPostLikeView.as_view(),
        name="community-post-like",
    ),
]
