from django.db.models import Q
from rest_framework import viewsets, filters 
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import Volume, Work
from .serializers import VolumeSerializer, WorkListSerializer, WorkDetailSerializer


class VolumeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Volume.objects.all().order_by("number", "id")
    serializer_class = VolumeSerializer


class WorkViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Work.objects.select_related("volume").all().order_by("id")

    filter_backends = [
        filters.SearchFilter,
        filters.OrderingFilter,
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

    multi_value_filter_fields = [
        "volume",
        "author",
        "genre",
        "language",
        "place",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        params = self.request.query_params

        for field in self.multi_value_filter_fields:
            values = [value for value in params.getlist(field) if value != ""]

            if values:
                queryset = queryset.filter(**{f"{field}__in": values})

        date_query = self.build_range_query("date", params)
        if date_query:
            queryset = queryset.filter(date_query)

        page_query = self.build_range_query("page_number", params, numeric=True)
        if page_query:
            queryset = queryset.filter(page_query)

        return queryset

    def build_range_query(self, field: str, params, numeric: bool = False):
        exact_values = self.clean_filter_values(params.getlist(field), numeric)
        range_values = params.getlist(f"{field}_range")
        from_values = self.clean_filter_values(params.getlist(f"{field}_from"), numeric)
        to_values = self.clean_filter_values(params.getlist(f"{field}_to"), numeric)

        query = Q()

        if exact_values:
            query |= Q(**{f"{field}__in": exact_values})

        for value in range_values:
            if ".." not in value:
                continue

            from_value, to_value = value.split("..", 1)
            range_query = self.make_range_query(field, from_value, to_value, numeric)

            if range_query:
                query |= range_query

        max_length = max(len(from_values), len(to_values))

        for index in range(max_length):
            from_value = from_values[index] if index < len(from_values) else ""
            to_value = to_values[index] if index < len(to_values) else ""
            range_query = self.make_range_query(field, from_value, to_value, numeric)

            if range_query:
                query |= range_query

        return query

    def make_range_query(self, field: str, from_value, to_value, numeric: bool = False):
        from_values = self.clean_filter_values([from_value], numeric)
        to_values = self.clean_filter_values([to_value], numeric)

        range_query = Q()

        if from_values:
            range_query &= Q(**{f"{field}__gte": from_values[0]})

        if to_values:
            range_query &= Q(**{f"{field}__lte": to_values[0]})

        return range_query

    def clean_filter_values(self, values, numeric: bool = False):
        cleaned_values = [value for value in values if value != ""]

        if not numeric:
            return cleaned_values

        return [value for value in cleaned_values if str(value).isdigit()]

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
            "dates": list(
                Work.objects.exclude(date="")
                .values_list("date", flat=True)
                .distinct()
                .order_by("date")
            ),
            "page_numbers": list(
                Work.objects.exclude(page_number__isnull=True)
                .values_list("page_number", flat=True)
                .distinct()
                .order_by("page_number")
            ),
        })
