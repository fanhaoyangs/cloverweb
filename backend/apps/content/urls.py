from django.urls import path

from .admin_views import (
    AdminArticleDetailView,
    AdminArticleListView,
    AdminCategoryListView,
    AdminSitePageDetailView,
    AdminSitePageListView,
)
from .views import ArticleDetailView, ArticleListView, SitePageDetailView

urlpatterns = [
    # 公开
    path('articles/', ArticleListView.as_view()),
    path('articles/<slug:slug>/', ArticleDetailView.as_view()),
    path('sitepage/<slug:slug>/', SitePageDetailView.as_view()),
    # CMS 管理（需 is_staff）
    path('admin/articles/', AdminArticleListView.as_view()),
    path('admin/articles/<int:pk>/', AdminArticleDetailView.as_view()),
    path('admin/categories/', AdminCategoryListView.as_view()),
    path('admin/sitepages/', AdminSitePageListView.as_view()),
    path('admin/sitepages/<slug:slug>/', AdminSitePageDetailView.as_view()),
]
