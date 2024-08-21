from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    pass


class UserTelegramBinding(models.Model):
    account_id = models.BigIntegerField()
    name = models.CharField(max_length=255)
    session_string = models.TextField()
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    fetched_channels = models.JSONField(default=list)


class Project(models.Model):
    name = models.CharField(max_length=255)
    owner = models.ForeignKey(to=User, on_delete=models.CASCADE)
    participants = models.ManyToManyField(
        to=User, related_name="participants", blank=True
    )
    preview_channel = models.ForeignKey(
        to="Channel",
        on_delete=models.SET_NULL,
        null=True,
        related_name="preview_for_projects",
    )


class Post(models.Model):
    project = models.ForeignKey(
        to=Project, on_delete=models.CASCADE, related_name="posts"
    )
    name = models.CharField(max_length=255)
    text = models.TextField()
    target_channels = models.ManyToManyField(
        to="Channel", related_name="target_channels", blank=True
    )
    schedule_time = models.DateTimeField(null=True)
    is_sent = models.BooleanField(default=False)
    stat_notified = models.BooleanField(default=False)
    stage = models.ForeignKey(to="WorkflowStage",
                              on_delete=models.SET_NULL, null=True)


class Channel(models.Model):
    project = models.ForeignKey(
        to=Project, on_delete=models.CASCADE, related_name="channels"
    )
    type = models.CharField(max_length=255)
    # Views are not available for groups
    is_group = models.BooleanField()
    name = models.CharField(max_length=255)
    channel_id = models.CharField(max_length=255)
    notify_at_views = models.IntegerField(default=500)
    binding = models.ForeignKey(
        to=UserTelegramBinding, on_delete=models.RESTRICT,
    )


class IssuedToken(models.Model):
    token = models.TextField()
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    date_of_issue = models.DateTimeField(auto_now_add=True, blank=True)
    is_invalidated = models.BooleanField(default=False)


class PostWatch(models.Model):
    post = models.ForeignKey(to=Post, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)


class PostMeasurement(models.Model):
    post = models.ForeignKey(to=Post, on_delete=models.CASCADE)
    channel = models.ForeignKey(to=Channel, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    views = models.IntegerField()
    engagement_rate = models.FloatField()
    reactions = models.IntegerField()


class Notification(models.Model):
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    issued_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField()
    is_read = models.BooleanField(default=False)

    @classmethod
    def notify_users(cls, users, text):
        for user in users:
            notification = Notification(
                user=user,
                text=text
            )
            notification.save()


def get_filepath(instance, filename):
    return f'files/{instance.post.pk}_{filename}'


class PostFile(models.Model):
    post = models.ForeignKey(
        to=Post, on_delete=models.CASCADE, related_name='files'
    )
    file = models.FileField(upload_to=get_filepath)
    is_video_note = models.BooleanField(default=False)


class FileUploadedToTelegram(models.Model):
    file = models.ForeignKey(to=PostFile, on_delete=models.CASCADE)
    binding = models.ForeignKey(to=UserTelegramBinding, on_delete=models.CASCADE)
    chat_id = models.BigIntegerField()
    message_id = models.IntegerField()


class PublishedPost(models.Model):
    post = models.ForeignKey(to=Post, on_delete=models.CASCADE)
    channel = models.ForeignKey(to=Channel, on_delete=models.CASCADE)
    message_id = models.IntegerField()


class WorkflowStage(models.Model):
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    color = models.CharField(max_length=6, default="00FF00")
    next_stage = models.ForeignKey(to="WorkflowStage",
                                   on_delete=models.SET_NULL, null=True)
    is_end = models.BooleanField()


class WorkflowPush(models.Model):
    project = models.ForeignKey(to=Project, on_delete=models.CASCADE)
    from_stage = models.ForeignKey(to=WorkflowStage,
                                   on_delete=models.CASCADE,
                                   null=True,
                                   related_name="sources_at")
    to_stage = models.ForeignKey(to=WorkflowStage,
                                 on_delete=models.CASCADE,
                                 null=True,
                                 related_name="ends_at")
    user = models.ForeignKey(to=User, on_delete=models.CASCADE)
    pushed_at = models.DateTimeField(auto_now_add=True)
    post = models.ForeignKey(to=Post, on_delete=models.CASCADE)
