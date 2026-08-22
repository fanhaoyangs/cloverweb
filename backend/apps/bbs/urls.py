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
    # 作者自编辑/自删除（时间窗内）
    path('my/topics/<int:pk>/', views.TopicEditView.as_view(), name='my-topic'),
    path('my/topics/<int:topic_pk>/posts/<int:pk>/', views.PostEditView.as_view(), name='my-post'),
    # 管理端（is_staff）
    path('admin/topics/<int:pk>/', views.AdminTopicDetailView.as_view(), name='admin-topic-detail'),
    path('admin/nodes/', views.AdminNodeListCreateView.as_view(), name='admin-nodes'),
    path('admin/nodes/<slug:slug>/', views.AdminNodeDetailView.as_view(), name='admin-node-detail'),
]
