from rest_framework import viewsets, filters
from .models import Volume, Work
from .serializers import VolumeSerializer, WorkListSerializer, WorkDetailSerializer
from django_filters.rest_framework import DjangoFilterBackend


class VolumeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Volume.objects.all().order_by("number", "id")
    serializer_class = VolumeSerializer


class WorkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Work.objects.select_related("volume").all().order_by("id")

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = [
        "volume",
        "author",
        "genre",
        "language",
        "place",
        "date_from",
        "date_to",
    ]

    search_fields = [
        "title",
        "title_short",
        "title_desc",
        "plain_text",
    ]

    ordering_fields = [
        "id",
        "title",
        "author",
        "genre",
        "date_from",
        "page_number",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return WorkListSerializer
        return WorkDetailSerializer