from datetime import datetime
from threading import Thread

from django.conf import settings
from pyrogram.errors import RPCError
from rest_framework.generics import RetrieveDestroyAPIView, ListAPIView
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import UserTelegramBinding
from api.permissions import IsOwner
from api.scheduler import scheduler
from api.serializers import BindingSerializer
from social_networks.tg import TelegramAuthorizer, TelegramPublisher


class BindingSendCodeView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        if "phone" not in request.data:
            return Response({"error": "no phone"}, 400)
        test_mode = settings.DEBUG and "test_mode" in request.data
        try:
            auth_id = TelegramAuthorizer().send_code(
                request.data["phone"], test_mode=test_mode
            )
        except RPCError as e:
            return Response({"error": str(e)}, 400)
        return Response({"auth_id": auth_id}, 200)


class BindingEnterCodeView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        if not isinstance(request.data.get("auth_id"), str):
            return Response({"error": "bad auth id"}, 400)
        if not isinstance(request.data.get("code"), str):
            return Response({"error": "bad code"}, 400)
        try:
            result = TelegramAuthorizer().enter_code(
                request.data["auth_id"], request.data["code"]
            )
            if not result.need_password:
                binding = UserTelegramBinding(
                    account_id=result.user.id,
                    session_string=result.session_string,
                    owner=request.user,
                    name=result.user.first_name,
                )
                binding.save()
                Thread(target=fetch_channels, args=(binding,)).start()
                return Response({"status": "ok"}, 200)
            else:
                return Response(
                    {"status": "need_password", "auth_id": result.auth_id}, 200
                )
        except RPCError as e:
            return Response({"error": str(e)}, 400)


class BindingEnterPasswordView(APIView):
    parser_classes = (JSONParser,)

    def post(self, request, *args, **kwargs):
        if not isinstance(request.data.get("auth_id"), str):
            return Response({"error": "bad auth id"}, 400)
        if not isinstance(request.data.get("password"), str):
            return Response({"error": "bad password"}, 400)
        try:
            auth_user = TelegramAuthorizer().enter_password(
                request.data["auth_id"], request.data["password"]
            )
            binding = UserTelegramBinding(
                account_id=auth_user.user.id,
                session_string=auth_user.session_string,
                owner=request.user,
                name=auth_user.user.first_name,
            )
            binding.save()
            Thread(target=fetch_channels, args=(binding,)).start()
            return Response({"status": "ok"}, 200)
        except RPCError as e:
            return Response({"error": str(e)}, 400)


class BindingListAPIView(ListAPIView):
    serializer_class = BindingSerializer
    queryset = UserTelegramBinding.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)


class BindingRetrieveDestroyAPIView(RetrieveDestroyAPIView):
    serializer_class = BindingSerializer
    permission_classes = (IsOwner, IsAuthenticated)
    queryset = UserTelegramBinding.objects.all()


class ChannelFromBindingsListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        channels = {}
        for binding in UserTelegramBinding.objects.filter(owner=request.user):
            for chan in binding.fetched_channels:
                if chan["name"] != "smm-client-preview":
                    channels[chan["id"]] = chan
        return Response(channels.values(), 200)


class BindingsChannelsReloadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        for binding in UserTelegramBinding.objects.filter(owner=request.user):
            Thread(target=fetch_channels, args=(binding,)).start()
        return Response({"status": "ok"}, 200)


def fetch_channels(binding: UserTelegramBinding):
    channels = []
    with TelegramPublisher(binding.session_string) as tg:
        for channel in tg.get_channels():
            channels.append(
                {
                    "id": channel.id,
                    "type": "telegram",
                    "name": channel.title,
                    "binding": binding.id,
                }
            )
    binding.fetched_channels = channels
    binding.save()
