from django.conf import settings as dj_settings
from django.db import transaction
from django.db.models import Count, F, Q
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .markdown_utils import md_to_excerpt, md_to_safe_html
from .models import Like, Node, Post, Topic
from .serializers import (
    AdminTopicUpdateSerializer,
    NodeAdminSerializer,
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
        q = (self.request.query_params.get('q') or '').strip()
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(content_md__icontains=q) | Q(excerpt__icontains=q))
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


# ---- 作者自编辑/自删除（时间窗内，见 EditWindowMixin）----


def _check_author_window(request, obj, is_topic=False):
    """作者 + 时间窗校验，失败直接抛 403/400 Response。"""
    if obj.author_id != request.user.id:
        return Response({'detail': '只能操作自己发布的内容'}, status=403)
    if not obj.within_edit_window():
        return Response(
            {'detail': f'发表超过 {dj_settings.BBS_EDIT_WINDOW_MINUTES} 分钟，不能修改或删除，请联系管理员'},
            status=400,
        )
    return None


class TopicEditView(APIView):
    """PATCH  /api/bbs/my/topics/<pk>/    编辑自己的话题（标题/正文）
    DELETE /api/bbs/my/topics/<pk>/    删除自己的话题（仅无回复时）
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        topic = get_object_or_404(Topic, pk=pk)
        err = _check_author_window(request, topic, is_topic=True)
        if err:
            return err
        title = (request.data.get('title') or topic.title).strip()
        content_md = (request.data.get('content_md') or topic.content_md).strip()
        if len(title) < 6:
            raise ValidationError('标题至少 6 个字')
        if len(content_md) < 3:
            raise ValidationError('正文太短了')
        topic.title = title
        topic.content_md = content_md
        topic.content_html = md_to_safe_html(content_md)
        topic.excerpt = md_to_excerpt(content_md)
        topic.edited_at = timezone.now()
        topic.save(update_fields=['title', 'content_md', 'content_html', 'excerpt', 'edited_at', 'updated_at'])
        out = TopicDetailSerializer(topic, context={'request': request})
        return Response(out.data)

    def delete(self, request, pk):
        topic = get_object_or_404(Topic, pk=pk)
        err = _check_author_window(request, topic, is_topic=True)
        if err:
            return err
        if topic.reply_count > 0:
            return Response({'detail': '已有回复的话题不能自行删除（会连带删除他人的讨论），请联系管理员处理'}, status=400)
        topic.delete()
        return Response(status=204)


class PostEditView(APIView):
    """PATCH  /api/bbs/my/topics/<topic_pk>/posts/<pk>/   编辑自己的回复
    DELETE /api/bbs/my/topics/<topic_pk>/posts/<pk>/   删除自己的回复（软删除留占位）
    """

    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, topic_pk, pk):
        post = get_object_or_404(Post, pk=pk, topic_id=topic_pk)
        err = _check_author_window(request, post)
        if err:
            return err
        if post.deleted:
            return Response({'detail': '该回复已删除'}, status=400)
        content_md = (request.data.get('content_md') or '').strip()
        if len(content_md) < 1:
            raise ValidationError('回复内容不能为空')
        post.content_md = content_md
        post.content_html = md_to_safe_html(content_md)
        post.edited_at = timezone.now()
        post.save(update_fields=['content_md', 'content_html', 'edited_at', 'updated_at'])
        out = PostSerializer(post, context={'request': request})
        return Response(out.data)

    def delete(self, request, topic_pk, pk):
        post = get_object_or_404(Post, pk=pk, topic_id=topic_pk)
        err = _check_author_window(request, post)
        if err:
            return err
        if post.deleted:
            return Response(status=204)
        # 软删除：清空正文保留楼层占位
        post.deleted = True
        post.content_md = ''
        post.content_html = ''
        post.save(update_fields=['deleted', 'content_md', 'content_html', 'updated_at'])
        return Response(status=204)


# ---- 管理端（is_staff）----
# 注：飞书登录用户当前全部 is_staff=True（CMS 内部用户语义，租户白名单控制
# 谁能登录），BBS 管理操作与 CMS 一致面向这批可信成员；P3 开放邮箱注册
# 时再细分普通用户/管理员权限模型。


class AdminTopicDetailView(generics.RetrieveUpdateDestroyAPIView):
    """管理话题：
    GET    /api/bbs/admin/topics/<id>/    详情
    PATCH  /api/bbs/admin/topics/<id>/    置顶/锁定（部分更新）
    DELETE /api/bbs/admin/topics/<id>/    删除（级联删除楼层与点赞）
    """

    permission_classes = [permissions.IsAdminUser]
    queryset = Topic.objects.select_related('node', 'author', 'last_reply_user')

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return AdminTopicUpdateSerializer
        return TopicListSerializer


class AdminNodeListCreateView(generics.ListCreateAPIView):
    """GET/POST /api/bbs/admin/nodes/ 板块管理（含停用板块）。"""

    permission_classes = [permissions.IsAdminUser]
    serializer_class = NodeAdminSerializer
    pagination_class = None

    def get_queryset(self):
        return (
            Node.objects.all()
            .annotate(topic_count=Count('topics'))
            .order_by('order', 'id')
        )


class AdminNodeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """PATCH/DELETE /api/bbs/admin/nodes/<slug>/ 改板块/删板块。"""

    permission_classes = [permissions.IsAdminUser]
    serializer_class = NodeAdminSerializer
    lookup_field = 'slug'

    def get_queryset(self):
        return Node.objects.all()

    def destroy(self, request, *args, **kwargs):
        node = self.get_object()
        if node.topics.exists():
            return Response(
                {'detail': f'板块下还有 {node.topics.count()} 个话题，请先在话题管理中处理后再删除'},
                status=400,
            )
        return super().destroy(request, *args, **kwargs)
