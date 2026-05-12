from django.db.models import Q
from django.db import transaction
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework import viewsets, filters 
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .models import SentimentFragmentLabel, Volume, Work
from .serializers import VolumeSerializer, WorkListSerializer, WorkDetailSerializer
from .services.tei_parser import parse_single_work, parse_volume


class VolumeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Volume.objects.all().order_by("number", "id")
    serializer_class = VolumeSerializer


class XMLUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    allowed_content_types = {"text/xml", "application/xml"}

    def post(self, request):
        upload_mode = request.data.get("mode")
        xml_files = request.FILES.getlist("files") or request.FILES.getlist("file")

        if upload_mode not in {"volume", "work"}:
            return Response(
                {"detail": "Укажите режим загрузки: volume или work"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not xml_files:
            return Response(
                {"detail": "Загрузите один или несколько XML-файлов"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invalid_files = [xml_file.name for xml_file in xml_files if not self.is_xml_file(xml_file)]

        if invalid_files:
            return Response(
                {"detail": f"Можно загружать только XML-файлы: {', '.join(invalid_files)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_volumes = []
        created_works = []

        try:
            for xml_file in xml_files:
                volume = Volume.objects.create(xml_file=xml_file)
                created_volumes.append(volume)

                if upload_mode == "volume":
                    created_works.extend(parse_volume(volume))
                else:
                    created_works.append(parse_single_work(volume))
        except Exception as exc:
            for volume in created_volumes:
                volume.delete()

            return Response(
                {"detail": str(exc) or "Не удалось разобрать XML"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "mode": upload_mode,
                "volume": VolumeSerializer(created_volumes[0], context={"request": request}).data,
                "volumes": VolumeSerializer(created_volumes, many=True, context={"request": request}).data,
                "works": WorkListSerializer(created_works, many=True).data,
            },
            status=status.HTTP_201_CREATED,
        )

    def is_xml_file(self, xml_file):
        return (
            xml_file.name.lower().endswith(".xml") or
            xml_file.content_type in self.allowed_content_types
        )


class SentimentAnnotationTaskView(APIView):
    default_genre = "письм"
    default_segment_size = 50

    def get(self, request):
        genre = request.query_params.get("genre", self.default_genre)
        segment_size = self.get_segment_size(request)

        work = (
            Work.objects.select_related("volume")
            .filter(genre__icontains=genre)
            .exclude(plain_text="")
            .filter(sentiment_labels__isnull=True)
            .order_by("id")
            .first()
        )

        if not work:
            return Response(
                {"detail": "Нет неразмеченных писем для выбранного жанра"},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response({
            "work": WorkDetailSerializer(work).data,
            "segment_size": segment_size,
            "fragments": self.build_fragments(work.plain_text, segment_size),
        })

    @transaction.atomic
    def post(self, request):
        work_id = request.data.get("work_id")
        fragments = request.data.get("fragments", [])

        if not work_id:
            return Response(
                {"detail": "Не указан work_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not fragments:
            return Response(
                {"detail": "Нет фрагментов для сохранения"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        work = Work.objects.filter(id=work_id).first()

        if not work:
            return Response(
                {"detail": "Произведение не найдено"},
                status=status.HTTP_404_NOT_FOUND,
            )

        invalid_fragment = next(
            (
                fragment for fragment in fragments
                if fragment.get("label") not in dict(SentimentFragmentLabel.LABEL_CHOICES)
            ),
            None,
        )

        if invalid_fragment:
            return Response(
                {"detail": "Укажите тональность для каждого фрагмента"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        SentimentFragmentLabel.objects.filter(work=work).delete()

        labels = [
            SentimentFragmentLabel(
                work=work,
                segment_index=fragment["segment_index"],
                word_start=fragment["word_start"],
                word_end=fragment["word_end"],
                text=fragment["text"],
                label=fragment["label"],
                comment=fragment.get("comment", ""),
            )
            for fragment in fragments
        ]

        SentimentFragmentLabel.objects.bulk_create(labels)

        return Response({
            "work_id": work.id,
            "saved": len(labels),
        }, status=status.HTTP_201_CREATED)

    def get_segment_size(self, request):
        raw_segment_size = request.query_params.get("segment_size", self.default_segment_size)

        try:
            segment_size = int(raw_segment_size)
        except (TypeError, ValueError):
            return self.default_segment_size

        if segment_size < 10 or segment_size > 300:
            return self.default_segment_size

        return segment_size

    def build_fragments(self, text: str, segment_size: int):
        words = text.split()
        fragments = []

        for segment_index, start in enumerate(range(0, len(words), segment_size)):
            end = min(start + segment_size, len(words))

            fragments.append({
                "segment_index": segment_index,
                "word_start": start,
                "word_end": end,
                "text": " ".join(words[start:end]),
                "label": "",
                "comment": "",
            })

        return fragments


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
