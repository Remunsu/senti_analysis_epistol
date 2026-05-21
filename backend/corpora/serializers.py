from rest_framework import serializers
from .models import SentimentAnalysisRun, SentimentFragmentLabel, Volume, Work


class VolumeSerializer(serializers.ModelSerializer):
    works_count = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()
    pdf_name = serializers.SerializerMethodField()
    pdf_kind = serializers.SerializerMethodField()

    class Meta:
        model = Volume
        fields = [
            "id",
            "source_id",
            "number",
            "title",
            "title_short",
            "author",
            "xml_file",
            "uploaded_at",
            "works_count",
            "pdf_url",
            "pdf_name",
            "pdf_kind",
        ]

    def get_works_count(self, obj):
        annotated_count = getattr(obj, "works_count", None)

        if annotated_count is not None:
            return annotated_count

        return obj.works.count()

    def get_pdf_url(self, obj):
        return build_volume_pdf_url(obj, self.context.get("request"))

    def get_pdf_name(self, obj):
        return get_pdf_name(obj)

    def get_pdf_kind(self, obj):
        return get_pdf_kind(obj)


class WorkListSerializer(serializers.ModelSerializer):
    volume_title = serializers.CharField(source="volume.title_short", read_only=True)
    date = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = [
            "id",
            "volume",
            "volume_title",
            "source_id",
            "title",
            "title_short",
            "author",
            "recipient",
            "genre",
            "date",
            "date_from",
            "date_to",
            "place",
            "pages",
            "language",
            "number",
        ]

    def get_date(self, obj):
        return format_work_date(obj)


class WorkDetailSerializer(serializers.ModelSerializer):
    volume_title = serializers.CharField(source="volume.title", read_only=True)
    date = serializers.SerializerMethodField()
    volume_pdf_url = serializers.SerializerMethodField()
    volume_pdf_name = serializers.SerializerMethodField()
    volume_pdf_kind = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = "__all__"

    def get_date(self, obj):
        return format_work_date(obj)

    def get_volume_pdf_url(self, obj):
        return build_volume_pdf_url(obj.volume, self.context.get("request"))

    def get_volume_pdf_name(self, obj):
        return get_pdf_name(obj.volume)

    def get_volume_pdf_kind(self, obj):
        return get_pdf_kind(obj.volume)


def format_work_date(work):
    return format_work_date_values(work.date_from, work.date_to)


def format_work_date_values(date_from, date_to):
    if date_from and date_to and date_from != date_to:
        return f"{date_from}-{date_to}"

    return date_from or date_to


def build_volume_pdf_url(volume, request=None):
    if not volume.facsimile_file:
        return ""

    path = f"/api/volumes/{volume.id}/pdf-file/"

    if request:
        return request.build_absolute_uri(path)

    return path


def get_pdf_name(volume):
    if not volume.facsimile_file:
        return ""

    return volume.facsimile_file.name.rsplit("/", 1)[-1]


def get_pdf_kind(volume):
    name = get_pdf_name(volume).lower()

    if name.endswith(".pdf"):
        return "pdf"

    if name.endswith((".djvu", ".djv")):
        return "djvu"

    return ""


class SentimentFragmentLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentFragmentLabel
        fields = "__all__"


class SentimentAnalysisRunSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = SentimentAnalysisRun
        fields = [
            "id",
            "user",
            "username",
            "model_kind",
            "model_name",
            "segment_size",
            "max_segment_size",
            "window_step",
            "works_count",
            "results_count",
            "status",
            "error_message",
            "created_at",
        ]
        read_only_fields = fields
