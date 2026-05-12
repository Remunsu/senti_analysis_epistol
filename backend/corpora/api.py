import re
import threading

from django.db.models import Q
from django.db import close_old_connections, transaction
from django.http import QueryDict
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
from .services.sentiment_analyzer import MODEL_DISPLAY_NAME, analyze_fragments, split_text_into_word_segments
from .services.tei_parser import parse_volume


class VolumeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Volume.objects.all().order_by("number", "id")
    serializer_class = VolumeSerializer


class XMLUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    allowed_content_types = {"text/xml", "application/xml"}

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
            works = self.get_selected_works(request.data)

            if not works:
                return Response(
                    {"detail": "Выберите произведения для анализа"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            run = SentimentAnalysisRun.objects.create(
                model_kind="rubert",
                model_name=MODEL_DISPLAY_NAME,
                segment_size=segment_size,
                works_count=len(works),
                status="running",
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc) or "Не удалось запустить анализ"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        work_ids = [work.id for work in works]
        analysis_thread = threading.Thread(
            target=self.run_analysis,
            args=(run.id, work_ids, segment_size),
            daemon=True,
        )
        analysis_thread.start()

        return Response(
            {
                "run": SentimentAnalysisRunSerializer(run).data,
                "results_count": 0,
            },
            status=status.HTTP_202_ACCEPTED,
        )

    @staticmethod
    def run_analysis(run_id, work_ids, segment_size):
        close_old_connections()

        try:
            run = SentimentAnalysisRun.objects.get(id=run_id)
            works = Work.objects.filter(id__in=work_ids).exclude(plain_text="").order_by("id")
            results_count = 0

            for work in works:
                fragments = split_text_into_word_segments(work.plain_text, segment_size)
                analysis_results = analyze_fragments(fragments)

                result_objects = [
                    SentimentAnalysisResult(
                        run=run,
                        work=work,
                        segment_index=result["segment_index"],
                        word_start=result["word_start"],
                        word_end=result["word_end"],
                        text=result["text"],
                        label=result["label"],
                        confidence=result["confidence"],
                    )
                    for result in analysis_results
                ]

                SentimentAnalysisResult.objects.bulk_create(result_objects, batch_size=500)
                results_count += len(result_objects)
                SentimentAnalysisRun.objects.filter(id=run.id).update(results_count=results_count)
        except Exception as exc:
            SentimentAnalysisResult.objects.filter(run_id=run_id).delete()
            SentimentAnalysisRun.objects.filter(id=run_id).update(
                status="failed",
                error_message=str(exc) or "Не удалось выполнить анализ",
                results_count=0,
            )
        else:
            SentimentAnalysisRun.objects.filter(id=run_id).update(
                status="completed",
                results_count=results_count,
            )
        finally:
            close_old_connections()


    def get_selected_works(self, data):
        queryset = Work.objects.exclude(plain_text="")

        if data.get("all_filtered"):
            params = QueryDict(data.get("filters_query", ""), mutable=False)
            queryset = self.apply_work_filters(queryset, params)
            return list(queryset.order_by("id"))

        work_ids = data.get("work_ids", [])

        return list(queryset.filter(id__in=work_ids).order_by("id"))

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
        by_work = {}

        result_rows = results.values(
            "work_id",
            "work__title",
            "work__author",
            "work__date",
            "work__genre",
            "work__place",
            "label",
        )

        for result in result_rows:
            work_summary = by_work.setdefault(
                result["work_id"],
                {
                    "work_id": result["work_id"],
                    "title": result["work__title"],
                    "author": result["work__author"],
                    "date": result["work__date"],
                    "genre": result["work__genre"],
                    "place": result["work__place"],
                    "year": self.extract_year(result["work__date"]),
                    "segments_count": 0,
                    "negative_count": 0,
                    "neutral_count": 0,
                    "positive_count": 0,
                    "score_sum": 0,
                },
            )
            score = int(result["label"])

            work_summary["segments_count"] += 1
            work_summary["score_sum"] += score

            if score < 0:
                work_summary["negative_count"] += 1
            elif score > 0:
                work_summary["positive_count"] += 1
            else:
                work_summary["neutral_count"] += 1

        summaries = []

        for work_summary in by_work.values():
            segments_count = work_summary["segments_count"] or 1
            mean_score = work_summary["score_sum"] / segments_count

            summaries.append({
                **work_summary,
                "mean_score": mean_score,
                "negative_share": work_summary["negative_count"] / segments_count,
                "neutral_share": work_summary["neutral_count"] / segments_count,
                "positive_share": work_summary["positive_count"] / segments_count,
            })

        return sorted(summaries, key=lambda item: item["work_id"])

    def extract_year(self, date_value):
        if not date_value:
            return ""

        match = re.search(r"\d{4}", str(date_value))

        return match.group(0) if match else ""

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
            label = item.get(field) or f"Без {'года' if field == 'year' else 'места'}"
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
            return sorted(grouped_items, key=lambda item: item["label"])

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
