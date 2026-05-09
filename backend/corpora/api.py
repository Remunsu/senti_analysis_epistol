from rest_framework import viewsets
from .models import Volume, Work
from .serializers import VolumeSerializer, WorkListSerializer, WorkDetailSerializer


class VolumeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Volume.objects.all().order_by("number", "id")
    serializer_class = VolumeSerializer


class WorkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Work.objects.select_related("volume").all().order_by("id")

    def get_serializer_class(self):
        if self.action == "list":
            return WorkListSerializer
        return WorkDetailSerializer