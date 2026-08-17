"""CMS 管理 API 视图（仅 is_staff，飞书登录用户 / superuser）。"""
from django.db.models import Q
from rest_framework import generics, permissions

from apps.team.models import SitePage

from .admin_serializers import (
    ArticleAdminSerializer,
    CategoryAdminSerializer,
    SitePageAdminSerializer,
)
from .models import Article, Category


class AdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class AdminArticleListView(generics.ListCreateAPIView):
    """GET /api/admin/articles/?status=&search=&category=&page=
    POST /api/admin/articles/（author 自动取当前用户）
    """

    serializer_class = ArticleAdminSerializer
    permission_classes = [AdminPermission]

    def get_queryset(self):
        qs = Article.objects.select_related('category', 'author').prefetch_related('tags')
        params = self.request.query_params
        status = params.get('status')
        if status:
            qs = qs.filter(status=status)
        category = params.get('category')
        if category:
            qs = qs.filter(category__slug=category)
        search = params.get('search')
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(excerpt__icontains=search))
        return qs


class AdminArticleDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ArticleAdminSerializer
    permission_classes = [AdminPermission]
    queryset = Article.objects.select_related('category', 'author').prefetch_related('tags')


class AdminCategoryListView(generics.ListCreateAPIView):
    serializer_class = CategoryAdminSerializer
    permission_classes = [AdminPermission]
    queryset = Category.objects.all().order_by('order', 'id')

    def perform_create(self, serializer):
        # slug 缺省自动生成（SlugField 仅 ascii，中文名无法直接用）
        if not serializer.validated_data.get('slug'):
            from django.utils.text import slugify
            name = serializer.validated_data['name']
            base = slugify(name) or 'cat'
            slug = base
            i = 1
            while Category.objects.filter(slug=slug).exists():
                i += 1
                slug = f'{base}-{i}'
            serializer.save(slug=slug[:64])
        else:
            serializer.save()


class AdminSitePageListView(generics.ListAPIView):
    serializer_class = SitePageAdminSerializer
    permission_classes = [AdminPermission]
    queryset = SitePage.objects.all().order_by('slug')


class AdminSitePageDetailView(generics.RetrieveUpdateAPIView):
    """PUT /api/admin/sitepages/<slug>/ 更新 title / content_html。"""

    serializer_class = SitePageAdminSerializer
    permission_classes = [AdminPermission]
    queryset = SitePage.objects.all()
    lookup_field = 'slug'
