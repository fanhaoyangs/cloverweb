from django.db import transaction
from django.db.models import Count, F
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .markdown_utils import md_to_safe_html
from .models import Like, Node, Post, Topic
from .serializers import (
    NodeSerializer,
    PostCreateSerializer,
    PostSerializer,
    TopicCreateSerializer,
    TopicDetailSerializer,
    TopicListSerializer,
)


class NodeListView(generics.ListAPIView):
    """GET /api/bbs/nodes/ 板块列表（含话题数）。板块数量少，不分页。"""

    serializer_class = NodeSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Node.objects.filter(is_active=True)
            .annotate(topic_count=Count('topics'))
            .order_by('order', 'id')
        )


class TopicListView(generics.ListCreateAPIView):
    """GET  /api/bbs/topics/?node=<slug>&sort=latest|replies&page=
    POST /api/bbs/topics/（登录；staff_only 板块仅 is_staff）

    列表不返回 content_html（同管理端列表瘦身原则）。
    """

    def get_serializer_class(self):
        return TopicCreateSerializer if self.request.method == 'POST' else TopicListSerializer

    def get_queryset(self):
        qs = Topic.objects.select_related('node', 'author', 'last_reply_user')
        node = self.request.query_params.get('node')
        if node:
            qs = qs.filter(node__slug=node)
        # last_reply_at 为 NULL 的话题：PG DESC 默认 NULLS FIRST，
        # Coalesce 归一到 created_at 保证"最后活跃"语义
        qs = qs.annotate(last_active=Coalesce('last_reply_at', 'created_at'))
        if self.request.query_params.get('sort') == 'replies':
            return qs.order_by('-is_pinned', '-reply_count', '-created_at')
        return qs.order_by('-is_pinned', '-last_active', '-created_at')

    def create(self, request, *args, **kwargs):
        node_slug = request.data.get('node')
        node = Node.objects.filter(slug=node_slug, is_active=True).first()
        if node and node.staff_only and not request.user.is_staff:
            return Response({'detail': '该板块仅管理员可发帖'}, status=403)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        # 输出用列表序列化器（含 id/node/author 等，前端拿 id 跳转详情）
        out = TopicListSerializer(serializer.instance, context=self.get_serializer_context())
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=201, headers=headers)


class TopicDetailView(generics.RetrieveAPIView):
    """GET /api/bbs/topics/<id>/ 详情（含正文 HTML），浏览量 +1。"""

    serializer_class = TopicDetailSerializer
    queryset = Topic.objects.select_related('node', 'author', 'last_reply_user')

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        Topic.objects.filter(pk=instance.pk).update(view_count=F('view_count') + 1)
        return super().retrieve(request, *args, **kwargs)


class PostListView(generics.ListCreateAPIView):
    """GET  /api/bbs/topics/<topic_pk>/posts/?page= 楼层列表（不含楼主帖）
    POST /api/bbs/topics/<topic_pk>/posts/ 回复（登录；锁定话题拒绝）
    """

    def get_serializer_class(self):
        return PostCreateSerializer if self.request.method == 'POST' else PostSerializer

    def get_queryset(self):
        topic = get_object_or_404(Topic, pk=self.kwargs['topic_pk'])
        return topic.replies.select_related('author')

    def create(self, request, *args, **kwargs):
        serializer = PostCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content_md = serializer.validated_data['content_md'].strip()
        with transaction.atomic():
            # select_for_update 防并发下楼层号/回复计数错乱
            topic = Topic.objects.select_for_update().get(pk=self.kwargs['topic_pk'])
            if topic.is_closed:
                raise ValidationError('话题已锁定，无法回复')
            post = Post.objects.create(
                topic=topic,
                author=request.user,
                content_md=content_md,
                content_html=md_to_safe_html(content_md),
                floor=topic.reply_count + 2,  # 楼主帖为 1 楼
            )
            topic.reply_count += 1
            topic.last_reply_at = timezone.now()
            topic.last_reply_user = request.user
            topic.save(update_fields=['reply_count', 'last_reply_at', 'last_reply_user'])
        out = PostSerializer(post, context=self.get_serializer_context())
        headers = self.get_success_headers(out.data)
        return Response(out.data, status=201, headers=headers)


class TopicLikeView(APIView):
    """POST /api/bbs/topics/<pk>/like/ 点赞/取消（toggle）。"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        topic = get_object_or_404(Topic, pk=pk)
        like, created = Like.objects.get_or_create(user=request.user, topic=topic)
        if created:
            Topic.objects.filter(pk=pk).update(like_count=F('like_count') + 1)
        else:
            like.delete()
            Topic.objects.filter(pk=pk).update(like_count=F('like_count') - 1)
        topic.refresh_from_db(fields=['like_count'])
        return Response({'liked': created, 'like_count': topic.like_count})


class PostLikeView(APIView):
    """POST /api/bbs/topics/<topic_pk>/posts/<pk>/like/ 点赞/取消（toggle）。"""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, topic_pk, pk):
        post = get_object_or_404(Post, pk=pk, topic_id=topic_pk)
        like, created = Like.objects.get_or_create(user=request.user, post=post)
        if created:
            Post.objects.filter(pk=pk).update(like_count=F('like_count') + 1)
        else:
            like.delete()
            Post.objects.filter(pk=pk).update(like_count=F('like_count') - 1)
        post.refresh_from_db(fields=['like_count'])
        return Response({'liked': created, 'like_count': post.like_count})
