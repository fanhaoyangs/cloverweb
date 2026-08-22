from django.contrib.auth import get_user_model
from rest_framework import serializers

from .markdown_utils import md_to_excerpt, md_to_safe_html
from .models import Node, Post, Topic
User = get_user_model()


class UserMiniSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'avatar_url']

    def get_name(self, obj):
        return obj.display_name or obj.username


class NodeSerializer(serializers.ModelSerializer):
    topic_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Node
        fields = ['slug', 'name', 'description', 'icon', 'order', 'staff_only', 'topic_count']


class TopicListSerializer(serializers.ModelSerializer):
    node = NodeSerializer(read_only=True)
    author = UserMiniSerializer(read_only=True)
    last_reply_user = UserMiniSerializer(read_only=True)
    liked = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            'id', 'title', 'excerpt', 'node', 'author',
            'is_pinned', 'is_closed',
            'view_count', 'reply_count', 'like_count', 'liked',
            'last_reply_at', 'last_reply_user', 'created_at',
        ]

    def get_liked(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()


def _author_perms(obj, request, *, is_topic=False):
    """作者自编辑/自删除标记（时间窗内才为 True；话题有回复时不可自删）。"""
    user = request.user if request else None
    if not user or not user.is_authenticated or user.id != obj.author_id:
        return False, False
    if not obj.within_edit_window():
        return False, False
    can_delete = obj.reply_count == 0 if is_topic else not obj.deleted
    return True, can_delete


class TopicDetailSerializer(TopicListSerializer):
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + [
            'content_html', 'content_md', 'edited_at', 'can_edit', 'can_delete',
        ]

    def get_can_edit(self, obj):
        return _author_perms(obj, self.context.get('request'), is_topic=True)[0]

    def get_can_delete(self, obj):
        return _author_perms(obj, self.context.get('request'), is_topic=True)[1]


class TopicCreateSerializer(serializers.ModelSerializer):
    node = serializers.SlugRelatedField(
        slug_field='slug', queryset=Node.objects.filter(is_active=True),
    )

    class Meta:
        model = Topic
        fields = ['title', 'node', 'content_md']
        extra_kwargs = {'content_md': {'write_only': True}}

    def validate_title(self, value):
        value = value.strip()
        if len(value) < 6:
            raise serializers.ValidationError('标题至少 6 个字')
        return value

    def validate_content_md(self, value):
        value = (value or '').strip()
        if len(value) < 3:
            raise serializers.ValidationError('正文太短了')
        if len(value) > 20000:
            raise serializers.ValidationError('正文不能超过 20000 字')
        return value

    def create(self, validated_data):
        # HTML 由服务端渲染+消毒后落库（双份存储：md 供再编辑）
        validated_data['content_html'] = md_to_safe_html(validated_data['content_md'])
        validated_data['excerpt'] = md_to_excerpt(validated_data['content_md'])
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)


class PostSerializer(serializers.ModelSerializer):
    author = UserMiniSerializer(read_only=True)
    liked = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()

    class Meta:
        model = Post
        # content_md 供前端"引用回复"构造 blockquote（内容本就公开）
        fields = [
            'id', 'floor', 'content_md', 'content_html', 'author',
            'like_count', 'liked', 'created_at', 'edited_at', 'deleted',
            'can_edit', 'can_delete',
        ]

    def get_liked(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()

    def get_can_edit(self, obj):
        return _author_perms(obj, self.context.get('request'))[0]

    def get_can_delete(self, obj):
        return _author_perms(obj, self.context.get('request'))[1]


class PostCreateSerializer(serializers.Serializer):
    content_md = serializers.CharField(min_length=1, max_length=20000)


class AdminTopicUpdateSerializer(serializers.ModelSerializer):
    """管理端 PATCH：仅置顶/锁定两个字段可写。"""

    class Meta:
        model = Topic
        fields = ['is_pinned', 'is_closed']


class NodeAdminSerializer(serializers.ModelSerializer):
    """板块管理（读写），含话题数统计。slug 创建后也可改（话题外键按 id 关联不受影响）。"""

    topic_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Node
        fields = [
            'slug', 'name', 'description', 'icon',
            'order', 'is_active', 'staff_only', 'topic_count', 'created_at',
        ]
        read_only_fields = ['created_at']

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError('名称不能为空')
        return value
