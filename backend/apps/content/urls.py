from django.urls import path

from .views import ArticleDetailView, ArticleListView, SitePageDetailView

urlpatterns = [
    path('articles/', ArticleListView.as_view()),
    path('articles/<slug:slug>/', ArticleDetailView.as_view()),
    path('sitepage/<slug:slug>/', SitePageDetailView.as_view()),
]
