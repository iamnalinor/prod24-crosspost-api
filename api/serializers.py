import logging
from datetime import datetime
from threading import Thread
from typing import Any, Dict
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from social_networks.tg import preload_to_telegram
from . import models
from .models import PostFile
from .scheduler import scheduler


class RegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ["username", "password"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        return models.User.objects.create_user(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.User
        fields = ["id", "username"]


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)
        data["user"] = self.user
        return data


class PostFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.PostFile
        fields = "__all__"


class FileListSerializer(serializers.Serializer):
    files = serializers.ListField(
        child=serializers.FileField(
            max_length=100000, allow_empty_file=False, use_url=False
        )
    )

    def __init__(self, instance=None, data=empty, post=None, **kwargs):
        self.post = post
        self.form_data = data
        self.is_video_note = (
            isinstance(data, dict)
            and data.get("is_video_note", False) == "true"
        )
        super().__init__(instance, data, **kwargs)

    def create(self, validated_data):
        post_file = None
        files = validated_data.pop("files")
        post_files = []
        for file in files:
            post_file = PostFile(
                post=self.post, file=file, is_video_note=self.is_video_note
            )
            post_file.save()
            post_files.append(post_file)

        Thread(target=preload_to_telegram, args=(post_files,)).start()
        logging.warning(f"File {post_file.file.path} added for preload")
        return post_file


class PostSerializer(serializers.ModelSerializer):
    files = PostFileSerializer(many=True, read_only=True)

    class Meta:
        model = models.Post
        fields = [
            "id",
            "name",
            "text",
            "project",
            "schedule_time",
            "target_channels",
            "files",
            "is_sent",
            "stage"
        ]


class ChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Channel
        fields = [
            "id",
            "type",
            "is_group",
            "name",
            "channel_id",
            "binding",
            "project",
        ]

    def validate_type(self, value):
        if value != "telegram":
            raise serializers.ValidationError("type must be in ['telegram']")
        return value


class ProjectSerializer(serializers.ModelSerializer):
    channels = ChannelSerializer(many=True, read_only=True)
    posts = PostSerializer(many=True, read_only=True)

    class Meta:
        model = models.Project
        fields = [
            "id",
            "name",
            "owner",
            "participants",
            "channels",
            "posts",
            "preview_channel"
        ]


class BindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.UserTelegramBinding
        fields = ["id", "account_id", "name"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Notification
        fields = ["id", "text", "issued_at", "is_read"]


class PostMeasurementSerializer(serializers.ModelSerializer):
    channel = ChannelSerializer(read_only=True)

    class Meta:
        model = models.PostMeasurement
        fields = [
            "post",
            "channel",
            "created_at",
            "views",
            "engagement_rate",
            "reactions",
        ]
        read_only_fields = fields


class WorkflowStageSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.WorkflowStage
        fields = ["id", "name", "color", "next_stage", "project", "is_end"]


class WorkflowPushSerializer(serializers.ModelSerializer):
    post = PostSerializer(read_only=True)
    user = UserSerializer(read_only=True)
    from_stage = WorkflowStageSerializer(read_only=True)
    to_stage = WorkflowStageSerializer(read_only=True)
    project = ProjectSerializer(read_only=True)

    class Meta:
        model = models.WorkflowPush
        fields = [
            "id",
            "from_stage",
            "to_stage",
            "user",
            "pushed_at",
            "project",
            "post",
        ]
