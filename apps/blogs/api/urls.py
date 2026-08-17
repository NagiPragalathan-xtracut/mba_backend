"""Blog API routes."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.blogs.api.views import BlogCategoryViewSet, BlogImageViewSet, BlogViewSet

router = DefaultRouter()
router.register("blogs", BlogViewSet, basename="blog")
router.register("blog-categories", BlogCategoryViewSet, basename="blog-category")
router.register("blog-images", BlogImageViewSet, basename="blog-image")

app_name = "blogs_api"

urlpatterns = [path("", include(router.urls))]
