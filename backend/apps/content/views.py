from django.db.models import F
from rest_framework import generics

from apps.team.models import SitePage

from .models import Article
from .serializers import ArticleDetailSerializer, ArticleListSerializer, SitePageSerializer


class ArticleListView(generics.ListAPIView):
    """已发布文章列表。?category=<slug>&featured=1&section=home_news"""

    serializer_class = ArticleListSerializer

    def get_queryset(self):
        qs = Article.objects.filter(status='published').select_related('category')
        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category__slug=category)
        if self.request.query_params.get('featured') == '1':
            qs = qs.filter(is_featured=True)
        section = self.request.query_params.get('section')
        if section:
            qs = qs.filter(website_sections__contains=section)
        return qs


class ArticleDetailView(generics.RetrieveAPIView):
    lookup_field = 'slug'
    serializer_class = ArticleDetailSerializer
    queryset = Article.objects.filter(status='published').select_related('category', 'author')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Article.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        return super().retrieve(request, *args, **kwargs)


class SitePageDetailView(generics.RetrieveAPIView):
    """静态页内容（home / about / philosophy）。"""

    lookup_field = 'slug'
    serializer_class = SitePageSerializer
    queryset = SitePage.objects.all()
