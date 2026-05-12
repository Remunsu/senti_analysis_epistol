import re

from django.db.models import Count, Q
from django.db import transaction
from django.http import QueryDict
from django_q.tasks import async_task
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework import viewsets, filters 
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .models import SentimentAnalysisResult, SentimentAnalysisRun, SentimentFragmentLabel, Volume, Work
from .serializers import (
    SentimentAnalysisRunSerializer,
    VolumeSerializer,
    WorkListSerializer,
    WorkDetailSerializer,
)
from .services.sentiment_analyzer import MODEL_DISPLAY_NAME
from .services.tei_parser import parse_volume


class VolumeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Volume.objects.all().order_by("number", "id")
    serializer_class = VolumeSerializer


class XMLUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    allowed_content_types = {"text/xml", "application/xml", "application/octet-stream", ""}
    max_file_size = 100 * 1024 * 1024

    def post(self, request):
        upload_mode = request.data.get("mode", "volume")
        xml_files = request.FILES.getlist("files") or request.FILES.getlist("file")

        if upload_mode != "volume":
            return Response(
                {"detail": "Загрузка одного произведения отключена. Загружайте XML тома."},
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

        oversized_files = [xml_file.name for xml_file in xml_files if xml_file.size > self.max_file_size]

        if oversized_files:
            return Response(
                {"detail": f"XML-файлы слишком большие: {', '.join(oversized_files)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_volumes = []
        created_works = []

        try:
            for xml_file in xml_files:
                volume = Volume.objects.create(xml_file=xml_file)
                created_volumes.append(volume)
                created_works.extend(parse_volume(volume))
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
        content_type = (xml_file.content_type or "").split(";", 1)[0].strip().lower()

        return (
            xml_file.name.lower().endswith(".xml") and
            content_type in self.allowed_content_types
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


class WorkFilterMixin:
    multi_value_filter_fields = [
        "volume",
        "author",
        "genre",
        "language",
        "place",
    ]

    def apply_work_filters(self, queryset, params):
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

        search_value = params.get("search", "")
        if search_value:
            queryset = queryset.filter(
                Q(title__icontains=search_value) |
                Q(title_short__icontains=search_value) |
                Q(title_desc__icontains=search_value) |
                Q(plain_text__icontains=search_value)
            )

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


class SentimentAnalysisView(WorkFilterMixin, APIView):
    default_segment_size = 50

    def post(self, request):
        try:
            segment_size = self.get_segment_size(request.data.get("segment_size"))
            work_ids = self.get_selected_work_ids(request.data)

            if not work_ids:
                return Response(
                    {"detail": "Выберите произведения для анализа"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            run = SentimentAnalysisRun.objects.create(
                model_kind="rubert",
                model_name=MODEL_DISPLAY_NAME,
                segment_size=segment_size,
                works_count=len(work_ids),
                status="running",
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc) or "Не удалось запустить анализ"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            task_id = async_task(
                "corpora.tasks.run_sentiment_analysis",
                run.id,
                work_ids,
                segment_size,
            )
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc) or "Не удалось поставить анализ в очередь"
            run.save(update_fields=["status", "error_message"])

            return Response(
                {"detail": run.error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(
            {
                "run": SentimentAnalysisRunSerializer(run).data,
                "task_id": task_id,
                "results_count": 0,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    def get_selected_work_ids(self, data):
        queryset = Work.objects.exclude(plain_text="")

        if data.get("all_filtered"):
            params = QueryDict(data.get("filters_query", ""), mutable=False)
            queryset = self.apply_work_filters(queryset, params)
            return list(queryset.order_by("id").values_list("id", flat=True))

        work_ids = data.get("work_ids", [])

        return list(queryset.filter(id__in=work_ids).order_by("id").values_list("id", flat=True))

    def get_segment_size(self, raw_segment_size):
        try:
            segment_size = int(raw_segment_size or self.default_segment_size)
        except (TypeError, ValueError):
            return self.default_segment_size

        if segment_size < 10 or segment_size > 300:
            return self.default_segment_size

        return segment_size


class SentimentAnalysisResultsView(APIView):
    def get(self, request, run_id=None):
        try:
            run = self.get_run(run_id)

            if not run:
                return Response(
                    {"detail": "Результаты анализа не найдены"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            results = (
                SentimentAnalysisResult.objects
                .select_related("work")
                .filter(run=run)
                .order_by("work_id")
            )

            summary = self.build_summary(results)
        except Exception as exc:
            return Response(
                {"detail": str(exc) or "Не удалось загрузить результаты анализа"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "run": SentimentAnalysisRunSerializer(run).data,
            "summary": summary,
            "totals": self.build_totals(summary),
            "charts": {
                "years": self.build_grouped_summary(summary, "year"),
                "places": self.build_grouped_summary(summary, "place"),
            },
        })

    def get_run(self, run_id):
        if run_id:
            return SentimentAnalysisRun.objects.filter(id=run_id).first()

        return SentimentAnalysisRun.objects.order_by("-created_at").first()

    def build_summary(self, results):
        result_rows = results.values(
            "work_id",
            "work__title",
            "work__author",
            "work__date",
            "work__genre",
            "work__place",
        ).annotate(
            segments_count=Count("id"),
            negative_count=Count("id", filter=Q(label="-1")),
            neutral_count=Count("id", filter=Q(label="0")),
            positive_count=Count("id", filter=Q(label="1")),
        ).order_by("work_id")

        summaries = []

        for result in result_rows:
            segments_count = result["segments_count"] or 1
            score_sum = result["positive_count"] - result["negative_count"]
            mean_score = score_sum / segments_count

            summaries.append(
                {
                    "work_id": result["work_id"],
                    "title": result["work__title"],
                    "author": result["work__author"],
                    "date": result["work__date"],
                    "year": self.extract_date_group_label(result["work__date"]),
                    "genre": result["work__genre"],
                    "place": result["work__place"],
                    "segments_count": result["segments_count"],
                    "negative_count": result["negative_count"],
                    "neutral_count": result["neutral_count"],
                    "positive_count": result["positive_count"],
                    "score_sum": score_sum,
                    "mean_score": mean_score,
                    "negative_share": result["negative_count"] / segments_count,
                    "neutral_share": result["neutral_count"] / segments_count,
                    "positive_share": result["positive_count"] / segments_count,
                }
            )

        return summaries

    def extract_date_group_label(self, date_value):
        date_text = str(date_value or "").strip()

        if not date_text:
            return ""

        if "/" in date_text:
            return date_text

        match = re.search(r"\d{4}", date_text)

        return match.group(0) if match else date_text

    def build_totals(self, summaries):
        totals = {
            "total": 0,
            "negative": 0,
            "neutral": 0,
            "positive": 0,
        }

        for item in summaries:
            totals["total"] += item["segments_count"]
            totals["negative"] += item["negative_count"]
            totals["neutral"] += item["neutral_count"]
            totals["positive"] += item["positive_count"]

        return totals

    def build_grouped_summary(self, summaries, field):
        groups = {}

        for item in summaries:
            raw_label = item.get(field)
            label = str(raw_label) if raw_label else f"Без {'года' if field == 'year' else 'места'}"
            group = groups.setdefault(
                label,
                {
                    "label": label,
                    "works_count": 0,
                    "segments_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "positive_count": 0,
                    "score_sum": 0,
                },
            )

            group["works_count"] += 1
            group["segments_count"] += item["segments_count"]
            group["negative_count"] += item["negative_count"]
            group["neutral_count"] += item["neutral_count"]
            group["positive_count"] += item["positive_count"]
            group["score_sum"] += item["score_sum"]

        grouped_items = []

        for group in groups.values():
            segments_count = group["segments_count"] or 1

            grouped_items.append({
                **group,
                "mean_score": group["score_sum"] / segments_count,
                "negative_share": group["negative_count"] / segments_count,
                "neutral_share": group["neutral_count"] / segments_count,
                "positive_share": group["positive_count"] / segments_count,
            })

        if field == "year":
            return sorted(
                grouped_items,
                key=lambda item: (
                    not item["label"].isdigit(),
                    int(item["label"]) if item["label"].isdigit() else item["label"],
                ),
            )

        return sorted(grouped_items, key=lambda item: (-item["segments_count"], item["label"]))


class SentimentAnalysisRunsView(APIView):
    def get(self, request):
        runs = SentimentAnalysisRun.objects.order_by("-created_at")

        return Response({
            "results": SentimentAnalysisRunSerializer(runs, many=True).data,
        })


class WorkViewSet(WorkFilterMixin, viewsets.ReadOnlyModelViewSet):
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

    def get_queryset(self):
        queryset = super().get_queryset()
        return self.apply_work_filters(queryset, self.request.query_params)

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
