import logging

from rest_framework.generics import (ListCreateAPIView,
                                     RetrieveUpdateDestroyAPIView)
from rest_framework.permissions import IsAuthenticated

from api.models import Project
from api.permissions import IsOwner
from api.serializers import ProjectSerializer


class ProjectListCreateView(ListCreateAPIView):
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated, )
    queryset = Project.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(participants=self.request.user.id)

    def create(self, request, *args, **kwargs):
        logging.warning(request.data)
        if "participants" not in request.data:
            request.data["participants"] = []
        if request.user.id not in request.data["participants"]:
            request.data["participants"].append(request.user.id)
        request.data["owner"] = request.user.id
        return super().create(request, *args, **kwargs)


class ProjectRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = ProjectSerializer
    permission_classes = (IsAuthenticated, IsOwner)
    queryset = Project.objects.all()

    def patch(self, request, *args, **kwargs):
        if "participants" in request.data and request.user.id not in request.data["participants"]:
            request.data["participants"].append(request.user.id)
        return super().patch(request, *args, **kwargs)
