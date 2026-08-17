from rest_framework import serializers

from .models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = (
            'id', 'username', 'display_name', 'avatar_url', 'email',
            'is_staff', 'is_feishu_user', 'last_login_at',
        )
        read_only_fields = fields
