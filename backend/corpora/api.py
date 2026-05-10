from rest_framework import viewsets, filters 
from rest_framework.response import Response
from rest_framework.decorators import action
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
        "date",
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
        "date",
        "page_number",
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return WorkListSerializer
        return WorkDetailSerializer
    
    @action(detail=False, methods=["get"])
    def filters(self, request):
        return Response({
            "genres": list(
                Work.objects.exclude(genre="")
                .values_list("genre", flat=True)
                .distinct()
                .order_by("genre")
            ),
            "authors": list(
                Work.objects.exclude(author="")
                .values_list("author", flat=True)
                .distinct()
                .order_by("author")
            ),
            "languages": list(
                Work.objects.exclude(language="")
                .values_list("language", flat=True)
                .distinct()
                .order_by("language")
            ),
            "places": list(
                Work.objects.exclude(place="")
                .values_list("place", flat=True)
                .distinct()
                .order_by("place")
            ),
        })