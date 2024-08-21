from rest_framework.generics import (ListCreateAPIView,
                                     RetrieveUpdateDestroyAPIView, ListAPIView)
from rest_framework.permissions import IsAuthenticated

from api.models import Channel, WorkflowStage, WorkflowPush
from api.permissions import CanInteractWithCurrentProject
from api.serializers import WorkflowStageSerializer, WorkflowPushSerializer


class WorkflowStageListCreateView(ListCreateAPIView):
    serializer_class = WorkflowStageSerializer
    queryset = WorkflowStage.objects.all()
    permission_classes = (CanInteractWithCurrentProject,)

    def get_queryset(self):
        return super().get_queryset().filter(
            project__id=self.kwargs["project"]
        )

    def create(self, request, *args, **kwargs):
        request.data["project"] = self.kwargs["project"]
        return super().create(request, *args, **kwargs)


class WorkflowStageRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = WorkflowStageSerializer
    permission_classes = (CanInteractWithCurrentProject,)
    queryset = WorkflowStage.objects.all()


class WorkflowPushListView(ListAPIView):
    serializer_class = WorkflowPushSerializer
    permission_classes = (CanInteractWithCurrentProject,)
    queryset = WorkflowPush.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(
            project__id=self.kwargs["project"]
        ).order_by("pushed_at").reverse()
