from django.urls import path

from .admin_views import (
    AdminArticleDetailView,
    AdminArticleListView,
    AdminCategoryListView,
    AdminImageCropView,
    AdminSitePageDetailView,
    AdminSitePageListView,
)
from .feishu_views import (
    FeishuAuthorizeView,
    FeishuDocumentsView,
    FeishuHistoryView,
    FeishuImportView,
    FeishuLogsView,
    FeishuStatusView,
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
    # 图片裁剪（服务端处理）
    path('admin/images/crop/', AdminImageCropView.as_view()),
    # 飞书文档导入（user OAuth 模式）
    path('admin/feishu/authorize/', FeishuAuthorizeView.as_view()),
    path('admin/feishu/status/', FeishuStatusView.as_view()),
    path('admin/feishu/documents/', FeishuDocumentsView.as_view()),
    path('admin/feishu/import/', FeishuImportView.as_view()),
    path('admin/feishu/history/', FeishuHistoryView.as_view()),
    path('admin/feishu/logs/', FeishuLogsView.as_view()),
]
