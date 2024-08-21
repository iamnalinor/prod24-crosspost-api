from pyrogram.enums import ChatType
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    get_object_or_404,
)
from rest_framework.permissions import IsAuthenticated

from api.models import Channel, UserTelegramBinding
from api.permissions import (
    IsOwnerOfCurrentProject,
    CanInteractWithCurrentProject,
)
from api.serializers import ChannelSerializer
from social_networks.tg import TelegramPublisher


class ChannelListCreateView(ListCreateAPIView):
    serializer_class = ChannelSerializer
    queryset = Channel.objects.filter(name__iexact="smm-client-preview")
    permission_classes = (CanInteractWithCurrentProject, IsAuthenticated)

    def get_queryset(self):
        return (
            super().get_queryset().filter(project__id=self.kwargs["pk"])
        )

    def create(self, request, *args, **kwargs):
        request.data["project"] = self.kwargs["pk"]
        binding = get_object_or_404(UserTelegramBinding, id=request.data["binding"])
        with TelegramPublisher(binding.session_string) as t:
            chat = t.get_chat(request.data["channel_id"])
            request.data["name"] = chat.title
            request.data["is_group"] = chat.type == ChatType.SUPERGROUP
        return super().create(request, *args, **kwargs)


class ChannelRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ChannelSerializer
    permission_classes = (IsAuthenticated, CanInteractWithCurrentProject)
    queryset = Channel.objects.all()
