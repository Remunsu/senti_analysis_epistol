import csv
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.db.models import Count, Max, Q
from django.db import transaction
from django.http import FileResponse, HttpResponse, QueryDict
from django.utils.text import get_valid_filename
from django.utils.decorators import method_decorator
from django.views.decorators.clickjacking import xframe_options_exempt
from django_q.tasks import async_task
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework import filters, mixins, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action
from .models import (
    SentimentAnalysisResult,
    SentimentAnalysisRun,
    SentimentAnnotationSkip,
    SentimentFragmentLabel,
    Volume,
    Work,
)
from .serializers import (
    SentimentAnalysisRunSerializer,
    VolumeSerializer,
    WorkListSerializer,
    WorkDetailSerializer,
    format_work_date,
    format_work_date_values,
)
from .services.sentiment_analyzer import get_model_display_name
from .services.text_segments import (
    DEFAULT_MAX_SEGMENT_SIZE,
    DEFAULT_MIN_SEGMENT_SIZE,
    split_text_into_word_segments,
)
from .services.tei_parser import parse_volume


class EditableModelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    pass


class VolumeViewSet(EditableModelViewSet, mixins.DestroyModelMixin):
    queryset = Volume.objects.annotate(works_count=Count("works")).order_by("number", "id")
    serializer_class = VolumeSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    pdf_source_extensions = {".pdf", ".djvu", ".djv"}

    def perform_destroy(self, instance):
        delete_volume_and_files(instance)

    @action(detail=True, methods=["post"], url_path="pdf")
    def upload_pdf(self, request, pk=None):
        volume = self.get_object()
        source_file = request.FILES.get("file")

        if not source_file:
            return Response(
                {"detail": "Загрузите PDF или DJVU-файл"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        extension = Path(source_file.name).suffix.lower()

        if extension not in self.pdf_source_extensions:
            return Response(
                {"detail": "Можно загрузить только PDF, DJVU или DJV"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            save_volume_pdf(volume, source_file, extension)
        except DjvuConversionError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(VolumeSerializer(volume, context={"request": request}).data)

    @method_decorator(xframe_options_exempt)
    @action(detail=True, methods=["get"], url_path="pdf-file")
    def pdf_file(self, request, pk=None):
        volume = self.get_object()

        if not volume.facsimile_file:
            return Response(
                {"detail": "Для тома не загружен PDF или DJVU"},
                status=status.HTTP_404_NOT_FOUND,
            )

        content_type = get_pdf_content_type(volume.facsimile_file.name)
        file_handle = volume.facsimile_file.open("rb")

        return FileResponse(
            file_handle,
            as_attachment=False,
            filename=Path(volume.facsimile_file.name).name,
            content_type=content_type,
        )


def get_pdf_content_type(file_name):
    extension = Path(file_name).suffix.lower()

    if extension == ".pdf":
        return "application/pdf"

    if extension in {".djvu", ".djv"}:
        return "image/vnd.djvu"

    return "application/octet-stream"


def delete_volume_and_files(volume):
    xml_file = volume.xml_file
    pdf_file = volume.facsimile_file

    volume.delete()

    if xml_file:
        xml_file.delete(save=False)

    if pdf_file:
        pdf_file.delete(save=False)


class DjvuConversionError(Exception):
    pass


def save_volume_pdf(volume, source_file, extension):
    if extension == ".pdf":
        if volume.facsimile_file:
            volume.facsimile_file.delete(save=False)

        volume.facsimile_file = source_file
        volume.save(update_fields=["facsimile_file"])
        return

    save_converted_djvu(volume, source_file)


def save_converted_djvu(volume, source_file):
    ddjvu_path = shutil.which("ddjvu")

    if not ddjvu_path:
        raise DjvuConversionError(
            "Для загрузки DJVU установите DjVuLibre: нужна команда ddjvu для конвертации в PDF."
        )

    source_name = get_valid_filename(Path(source_file.name).stem) or "volume"
    pdf_name = f"{source_name}.pdf"

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_path = temp_path / f"{source_name}{Path(source_file.name).suffix.lower()}"
        output_path = temp_path / pdf_name

        with input_path.open("wb") as target:
            for chunk in source_file.chunks():
                target.write(chunk)

        try:
            subprocess.run(
                [ddjvu_path, "-format=pdf", str(input_path), str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            error_text = (exc.stderr or exc.stdout or "").strip()
            message = "Не удалось конвертировать DJVU в PDF"

            if error_text:
                message = f"{message}: {error_text}"

            raise DjvuConversionError(message) from exc

        with output_path.open("rb") as converted_pdf:
            if volume.facsimile_file:
                volume.facsimile_file.delete(save=False)

            volume.facsimile_file.save(pdf_name, File(converted_pdf), save=False)

    volume.save(update_fields=["facsimile_file"])


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
                delete_volume_and_files(volume)

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


class SentimentAnnotationCriteriaMixin:
    target_genre = "письмо"
    target_languages = ("ru", "de ru", "la ru")
    min_segment_size = DEFAULT_MIN_SEGMENT_SIZE
    max_segment_size = DEFAULT_MAX_SEGMENT_SIZE

    def get_annotation_queryset(self):
        return (
            Work.objects.select_related("volume")
            .filter(genre=self.target_genre, language__in=self.target_languages)
            .exclude(plain_text="")
        )

    def build_annotation_stats(self):
        queryset = self.get_annotation_queryset()
        total_count = queryset.count()
        labeled_count = queryset.filter(sentiment_labels__isnull=False).distinct().count()
        skipped_count = queryset.filter(sentiment_annotation_skip__isnull=False).count()
        labeled_fragments_count = SentimentFragmentLabel.objects.filter(work__in=queryset).count()
        remaining_fragments_count = self.count_remaining_annotation_fragments(queryset)

        return {
            "total_count": total_count,
            "labeled_count": labeled_count,
            "skipped_count": skipped_count,
            "remaining_count": max(total_count - labeled_count - skipped_count, 0),
            "labeled_fragments_count": labeled_fragments_count,
            "remaining_fragments_count": remaining_fragments_count,
        }

    def count_remaining_annotation_fragments(self, queryset):
        remaining_texts = (
            queryset
            .filter(sentiment_labels__isnull=True)
            .filter(sentiment_annotation_skip__isnull=True)
            .values_list("plain_text", flat=True)
        )

        return sum(
            len(
                split_text_into_word_segments(
                    text,
                    self.min_segment_size,
                    self.max_segment_size,
                )
            )
            for text in remaining_texts.iterator(chunk_size=500)
        )

    def build_annotation_criteria(self):
        return {
            "genre": self.target_genre,
            "languages": list(self.target_languages),
            "min_segment_size": self.min_segment_size,
            "max_segment_size": self.max_segment_size,
        }


class SentimentAnnotationTaskView(SentimentAnnotationCriteriaMixin, APIView):

    def get(self, request):
        work = (
            self.get_annotation_queryset()
            .filter(sentiment_labels__isnull=True)
            .filter(sentiment_annotation_skip__isnull=True)
            .order_by("id")
            .first()
        )

        payload = {
            "criteria": self.build_annotation_criteria(),
            **self.build_annotation_stats(),
            "work": None,
            "min_segment_size": self.min_segment_size,
            "max_segment_size": self.max_segment_size,
            "fragments": [],
        }

        if not work:
            return Response({
                **payload,
                "detail": "Нет неразмеченных писем для выбранных условий",
            })

        return Response({
            **payload,
            "work": WorkDetailSerializer(work).data,
            "fragments": self.build_fragments(work.plain_text),
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

        work = self.get_annotation_queryset().filter(id=work_id).first()

        if not work:
            return Response(
                {"detail": "Письмо не найдено или не входит в набор для разметки"},
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
        SentimentAnnotationSkip.objects.filter(work=work).delete()

        labels = [
            SentimentFragmentLabel(
                work=work,
                segment_index=fragment["segment_index"],
                word_start=fragment["word_start"],
                word_end=fragment["word_end"],
                text=fragment["text"],
                label=fragment["label"],
                comment="",
            )
            for fragment in fragments
        ]

        SentimentFragmentLabel.objects.bulk_create(labels)

        return Response({
            "work_id": work.id,
            "saved": len(labels),
            **self.build_annotation_stats(),
        }, status=status.HTTP_201_CREATED)

    def build_fragments(self, text: str):
        return [
            {
                **fragment,
                "label": "",
            }
            for fragment in split_text_into_word_segments(
                text,
                self.min_segment_size,
                self.max_segment_size,
            )
        ]


class SentimentAnnotationSkipView(SentimentAnnotationCriteriaMixin, APIView):
    def post(self, request):
        work_id = request.data.get("work_id")

        if not work_id:
            return Response(
                {"detail": "Не указан work_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        work = self.get_annotation_queryset().filter(id=work_id).first()

        if not work:
            return Response(
                {"detail": "Письмо не найдено или не входит в набор для разметки"},
                status=status.HTTP_404_NOT_FOUND,
            )

        SentimentFragmentLabel.objects.filter(work=work).delete()
        SentimentAnnotationSkip.objects.get_or_create(work=work)

        return Response({
            "work_id": work.id,
            **self.build_annotation_stats(),
        }, status=status.HTTP_201_CREATED)


class SentimentAnnotationExportView(SentimentAnnotationCriteriaMixin, APIView):
    def get(self, request):
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="sentiment_annotations.csv"'
        response.write("\ufeff")

        writer = csv.writer(response)
        writer.writerow([
            "work_id",
            "source_id",
            "volume_id",
            "volume_number",
            "volume_title",
            "work_number",
            "title",
            "author",
            "recipient",
            "genre",
            "language",
            "date_from",
            "date_to",
            "date",
            "place",
            "pages",
            "segment_index",
            "word_start",
            "word_end",
            "label",
            "text",
            "created_at",
        ])

        labels = (
            SentimentFragmentLabel.objects
            .select_related("work", "work__volume")
            .filter(work__in=self.get_annotation_queryset())
            .order_by("work_id", "segment_index")
        )

        for label in labels.iterator(chunk_size=1000):
            work = label.work
            volume = work.volume

            writer.writerow([
                work.id,
                work.source_id,
                volume.id,
                volume.number,
                volume.title,
                work.number,
                work.title,
                work.author,
                work.recipient,
                work.genre,
                work.language,
                work.date_from,
                work.date_to,
                format_work_date(work),
                work.place,
                work.pages,
                label.segment_index,
                label.word_start,
                label.word_end,
                label.label,
                label.text,
                label.created_at.isoformat(),
            ])

        return response


class WorkFilterMixin:
    multi_value_filter_fields = [
        "volume",
        "author",
        "recipient",
        "genre",
        "language",
        "place",
    ]

    def apply_work_filters(self, queryset, params):
        for field in self.multi_value_filter_fields:
            values = [value for value in params.getlist(field) if value != ""]

            if field == "volume":
                values = self.clean_filter_values(values, numeric=True)

            if values:
                queryset = queryset.filter(**{f"{field}__in": values})

        date_query = self.build_date_query(params)
        if date_query:
            queryset = queryset.filter(date_query)

        number_query = self.build_range_query("number", params, numeric=True)
        if number_query:
            queryset = queryset.filter(number_query)

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

    def build_date_query(self, params):
        exact_values = self.clean_filter_values(params.getlist("date"))
        range_values = params.getlist("date_range")
        from_values = self.clean_filter_values(params.getlist("date_from"))
        to_values = self.clean_filter_values(params.getlist("date_to"))

        query = Q()

        for value in exact_values:
            query |= Q(date_from=value) | Q(date_to=value)

        for value in range_values:
            if ".." not in value:
                continue

            from_value, to_value = value.split("..", 1)
            range_query = self.make_date_overlap_query(from_value, to_value)

            if range_query:
                query |= range_query

        max_length = max(len(from_values), len(to_values))

        for index in range(max_length):
            from_value = from_values[index] if index < len(from_values) else ""
            to_value = to_values[index] if index < len(to_values) else ""
            range_query = self.make_date_overlap_query(from_value, to_value)

            if range_query:
                query |= range_query

        return query

    def make_date_overlap_query(self, from_value, to_value):
        from_value = clean_filter_value(from_value)
        to_value = clean_filter_value(to_value)

        range_query = Q()

        if from_value:
            range_query &= Q(date_to__gte=from_value)

        if to_value:
            range_query &= Q(date_from__lte=to_value)

        return range_query

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


class SentimentRunMixin(WorkFilterMixin):
    default_min_segment_size = DEFAULT_MIN_SEGMENT_SIZE
    default_max_segment_size = DEFAULT_MAX_SEGMENT_SIZE

    def get_selected_work_ids(self, data):
        queryset = Work.objects.exclude(plain_text="")

        if data.get("all_filtered"):
            params = QueryDict(data.get("filters_query", ""), mutable=False)
            queryset = self.apply_work_filters(queryset, params)
            return list(queryset.order_by("id").values_list("id", flat=True))

        work_ids = data.get("work_ids", [])

        return list(queryset.filter(id__in=work_ids).order_by("id").values_list("id", flat=True))

    def get_segment_size(self, raw_segment_size, default_value):
        try:
            segment_size = int(raw_segment_size or default_value)
        except (TypeError, ValueError):
            return default_value

        if segment_size < 10 or segment_size > 300:
            return default_value

        return segment_size

    def create_run(self, work_ids, segment_size, max_segment_size=None, window_step=0):
        return SentimentAnalysisRun.objects.create(
            model_kind="rubert",
            model_name=get_model_display_name(),
            segment_size=segment_size,
            max_segment_size=max_segment_size,
            window_step=window_step,
            works_count=len(work_ids),
            status="running",
        )

    def enqueue_run(self, run, work_ids):
        try:
            return async_task(
                "corpora.tasks.run_sentiment_analysis",
                run.id,
                work_ids,
            )
        except Exception as exc:
            run.status = "failed"
            run.error_message = str(exc) or "Не удалось поставить анализ в очередь"
            run.save(update_fields=["status", "error_message"])
            raise


class SentimentAnalysisView(SentimentRunMixin, APIView):
    def post(self, request):
        try:
            min_segment_size = self.get_segment_size(
                request.data.get("min_segment_size") or request.data.get("segment_size"),
                self.default_min_segment_size,
            )
            max_segment_size = self.get_segment_size(
                request.data.get("max_segment_size"),
                self.default_max_segment_size,
            )

            if max_segment_size < min_segment_size:
                max_segment_size = max(min_segment_size, self.default_max_segment_size)

            work_ids = self.get_selected_work_ids(request.data)

            if not work_ids:
                return Response(
                    {"detail": "Выберите произведения для анализа"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            run = self.create_run(
                work_ids,
                segment_size=min_segment_size,
                max_segment_size=max_segment_size,
                window_step=0,
            )
        except Exception as exc:
            return Response(
                {"detail": str(exc) or "Не удалось запустить анализ"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            task_id = self.enqueue_run(run, work_ids)
        except Exception:
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


class SentimentSummaryMixin:
    def build_summary(self, results):
        result_rows = results.values(
            "original_work_id",
            "snapshot_title",
            "snapshot_author",
            "snapshot_recipient",
            "snapshot_date_from",
            "snapshot_date_to",
            "snapshot_genre",
            "snapshot_place",
        ).annotate(
            live_work_id=Max("work_id"),
            segments_count=Count("id"),
            negative_count=Count("id", filter=Q(label="-1")),
            neutral_count=Count("id", filter=Q(label="0")),
            positive_count=Count("id", filter=Q(label="1")),
        ).order_by("original_work_id")

        summaries = []

        for result in result_rows:
            segments_count = result["segments_count"] or 1
            score_sum = result["positive_count"] - result["negative_count"]
            mean_score = score_sum / segments_count

            summaries.append(
                {
                    "work_id": result["live_work_id"],
                    "original_work_id": result["original_work_id"],
                    "title": result["snapshot_title"],
                    "author": result["snapshot_author"],
                    "recipient": result["snapshot_recipient"],
                    "date": self.format_result_date(result),
                    "date_from": result["snapshot_date_from"],
                    "date_to": result["snapshot_date_to"],
                    "year": self.extract_year_from_date_to(result["snapshot_date_to"]),
                    "genre": result["snapshot_genre"],
                    "place": result["snapshot_place"],
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

    def format_result_date(self, result):
        date_from = result["snapshot_date_from"]
        date_to = result["snapshot_date_to"]

        if date_from and date_to and date_from != date_to:
            return f"{date_from}-{date_to}"

        return date_from or date_to

    def extract_year_from_date_to(self, date_to):
        date_text = str(date_to or "").strip()
        match = re.search(r"\d{4}", date_text)

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


class SentimentAnalysisResultsView(SentimentSummaryMixin, APIView):
    def get(self, request, run_id=None):
        try:
            run = self.get_run(run_id)

            if not run:
                return Response(
                    {"detail": "Результаты анализа не найдены"},
                    status=status.HTTP_404_NOT_FOUND,
                )

            results = SentimentAnalysisResult.objects.filter(run=run)

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


class SentimentAnalysisWorkFragmentsView(APIView):
    def get(self, request, run_id, original_work_id):
        run = SentimentAnalysisRun.objects.filter(id=run_id).first()

        if not run:
            return Response(
                {"detail": "Результаты анализа не найдены"},
                status=status.HTTP_404_NOT_FOUND,
            )

        fragments = list(
            SentimentAnalysisResult.objects
            .filter(run=run, original_work_id=original_work_id)
            .order_by("segment_index")
            .values(
                "segment_index",
                "word_start",
                "word_end",
                "text",
                "label",
                "confidence",
            )
        )

        return Response({
            "run": SentimentAnalysisRunSerializer(run).data,
            "original_work_id": original_work_id,
            "fragments": fragments,
        })


class SentimentAnalysisRunsView(APIView):
    def get(self, request):
        runs = SentimentAnalysisRun.objects.order_by("-created_at")

        return Response({
            "results": SentimentAnalysisRunSerializer(runs, many=True).data,
        })


class WorkViewSet(WorkFilterMixin, EditableModelViewSet):
    queryset = Work.objects.select_related("volume").all().order_by("id")

    filter_backends = [
        filters.OrderingFilter,
    ]

    ordering_fields = [
        "id",
        "title",
        "author",
        "genre",
        "date_from",
        "date_to",
        "number",
    ]

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = self.apply_work_filters(queryset, self.request.query_params)

        if self.action == "list":
            queryset = queryset.defer("plain_text", "raw_xml")

        return queryset

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
            "recipients": list(
                Work.objects.exclude(recipient="")
                .values_list("recipient", flat=True)
                .distinct()
                .order_by("recipient")
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
                sorted(
                    {
                        format_work_date_values(date_from, date_to)
                        for date_from, date_to in (
                            Work.objects.exclude(date_from="", date_to="")
                            .values_list("date_from", "date_to")
                            .distinct()
                        )
                        if format_work_date_values(date_from, date_to)
                    }
                )
            ),
            "numbers": list(
                Work.objects.exclude(number__isnull=True)
                .values_list("number", flat=True)
                .distinct()
                .order_by("number")
            ),
        })


def clean_filter_value(value):
    return str(value or "").strip()
