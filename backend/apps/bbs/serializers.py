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


class TopicDetailSerializer(TopicListSerializer):
    class Meta(TopicListSerializer.Meta):
        fields = TopicListSerializer.Meta.fields + ['content_html']


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

    class Meta:
        model = Post
        fields = ['id', 'floor', 'content_html', 'author', 'like_count', 'liked', 'created_at']

    def get_liked(self, obj):
        user = self.context.get('request').user if self.context.get('request') else None
        if not user or not user.is_authenticated:
            return False
        return obj.likes.filter(user=user).exists()


class PostCreateSerializer(serializers.Serializer):
    content_md = serializers.CharField(min_length=1, max_length=20000)
