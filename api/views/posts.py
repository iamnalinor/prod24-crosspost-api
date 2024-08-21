from datetime import timedelta, datetime, date

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    RetrieveAPIView,
    ListAPIView,
    CreateAPIView,
    RetrieveDestroyAPIView,
)
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from api.models import (
    Post,
    PostWatch,
    UserTelegramBinding,
    PostMeasurement,
    PostFile,
    Channel,
    WorkflowPush,
    Project,
)
from api.permissions import (
    IsOwnerOfCurrentProject,
    CanInteractWithCurrentProject,
)
from api.scheduler import (
    schedule_sending,
    unschedule_sending,
    watch_job,
    are_any_schedule_clashes,
    force_watch_for_post,
)
from api.serializers import (
    PostSerializer,
    PostMeasurementSerializer,
    PostFileSerializer,
    FileListSerializer,
)
from social_networks.tg import TelegramPublisher


def try_to_schedule(request, old_obj, obj):
    if request.data.get("schedule_time") is not None:
        if not UserTelegramBinding.objects.filter(owner=request.user).exists():
            return Response({"error": "no social network bindings"}, 400)
        schedule_sending(obj.id)
    elif request.data.get("schedule_time", -1) is None:
        unschedule_sending(obj.id)
    elif old_obj is not None and old_obj.schedule_time != obj.schedule_time:
        unschedule_sending(obj.id)
        if not UserTelegramBinding.objects.filter(owner=request.user).exists():
            return Response({"error": "no social network bindings"}, 400)
        schedule_sending(obj.id)
    return None


class PostListCreateView(ListCreateAPIView):
    serializer_class = PostSerializer
    queryset = Post.objects.all().order_by("-id")
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return super().get_queryset().filter(project__id=self.kwargs["pk"])

    def create(self, request, *args, **kwargs):
        project = Project.objects.get(id=self.kwargs["pk"])
        if not (project.owner == request.user or request.user in project.participants.all()):
            return Response({"error": "no access"}, 403)
        if "target_channels" not in request.data:
            request.data["target_channels"] = []
        request.data["project"] = self.kwargs["pk"]
        resp = super().create(request, *args, **kwargs)
        post = Post.objects.get(id=resp.data["id"])
        res = try_to_schedule(request, None, post)
        if res is not None:
            return res
        if are_any_schedule_clashes(post):
            resp.data._mutable = True
            resp.data["warning"] = "time clash"
        return resp


class PostRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = PostSerializer
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)
    queryset = Post.objects.all()

    def update(self, request, *args, **kwargs):
        old_object = self.get_object()
        resp = super().update(request, *args, **kwargs)
        post = self.get_object()
        res = try_to_schedule(request, old_object, post)
        if res is not None:
            return res
        if are_any_schedule_clashes(post):
            resp.data._mutable = True
            resp.data["warning"] = "time clash"
        if "stage" in request.data:
            push = WorkflowPush(
                project=self.get_object().project,
                user=self.request.user,
                from_stage=old_object.stage,
                to_stage=self.get_object().stage,
                post=self.get_object(),
            )
            push.save()
        return resp


class PostGeneratePreviewView(CreateAPIView):
    queryset = Post.objects.all()
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def create(self, request, **kwargs):
        post = self.get_object()

        binding = UserTelegramBinding.objects.filter(owner=request.user).last()

        with TelegramPublisher(binding.session_string) as tg:
            if post.project.preview_channel is None:
                chat = tg.ensure_channel("smm-client-preview")
                preview_channel, _ = Channel.objects.get_or_create(
                    project=post.project,
                    channel_id=chat.id,
                    type="telegram",
                    is_group=False,
                    name="smm-client-preview",
                    binding=binding,
                )
                post.project.preview_channel = preview_channel
                post.project.save()

            msg = tg.publish(
                post.project.preview_channel.channel_id,
                post,
            )

        return Response({"link": msg.link}, 200)


class PostStatListView(ListAPIView):
    serializer_class = PostMeasurementSerializer
    queryset = PostMeasurement.objects.filter(views__gt=1)
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def get_queryset(self):
        # force_watch_for_post(Post.objects.get(id=self.kwargs["post_id"]))
        if self.kwargs["days"] > 0:
            current_date = timezone.now().date()
            start_date = current_date - timedelta(days=self.kwargs["days"])
            return (
                super()
                .get_queryset()
                .filter(
                    post__id=self.kwargs["post_id"], created_at__gte=start_date
                )
            )
        else:
            return (
                super().get_queryset().filter(post__id=self.kwargs["post_id"])
            )


class UploadFilesView(APIView):
    parser_classes = (MultiPartParser,)
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def post(self, request, **kwargs):
        post = get_object_or_404(Post, id=kwargs["post_id"])
        serializer = FileListSerializer(post=post, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"status": "ok"}, status=201)


class PostFileListAPIView(ListAPIView):
    serializer_class = PostFileSerializer
    queryset = PostFile.objects.all()
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def get_queryset(self):
        return super().get_queryset().filter(post__id=self.kwargs["post_id"])


class PostFileRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    serializer_class = PostFileSerializer
    queryset = PostFile.objects.all()
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def get_queryset(self):
        return super().get_queryset().filter(post__id=self.kwargs["post_id"])


class GetUpcomingPostsForUser(APIView):
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def get(self, request):
        posts = []
        for project in Project.objects.all():
            if not (
                project.owner == request.user
                or request.user in project.participants.all()
            ):
                continue
            for post in Post.objects.filter(
                schedule_time__isnull=False
            ).filter(project=project, schedule_time__gte=timezone.now()):
                posts.append(post)
        calendar = {}
        for post in posts:
            post_date = post.schedule_time.date()
            post_date = post_date.isoformat()
            if post_date not in calendar:
                calendar[post_date] = []
            calendar[post_date].append(PostSerializer(post).data)
        return Response(calendar, 200)
