from django.urls import path

from . import views

app_name = 'bbs'

urlpatterns = [
    path('nodes/', views.NodeListView.as_view(), name='nodes'),
    path('topics/', views.TopicListView.as_view(), name='topics'),
    path('topics/<int:pk>/', views.TopicDetailView.as_view(), name='topic-detail'),
    path('topics/<int:pk>/like/', views.TopicLikeView.as_view(), name='topic-like'),
    path('topics/<int:topic_pk>/posts/', views.PostListView.as_view(), name='posts'),
    path('topics/<int:topic_pk>/posts/<int:pk>/like/', views.PostLikeView.as_view(), name='post-like'),
]
