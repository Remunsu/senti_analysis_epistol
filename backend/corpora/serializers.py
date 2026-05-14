from rest_framework import serializers
from .models import SentimentAnalysisRun, SentimentFragmentLabel, Volume, Work


class VolumeSerializer(serializers.ModelSerializer):
    works_count = serializers.SerializerMethodField()
    facsimile_url = serializers.SerializerMethodField()
    facsimile_name = serializers.SerializerMethodField()
    facsimile_kind = serializers.SerializerMethodField()

    class Meta:
        model = Volume
        fields = "__all__"

    def get_works_count(self, obj):
        annotated_count = getattr(obj, "works_count", None)

        if annotated_count is not None:
            return annotated_count

        return obj.works.count()

    def get_facsimile_url(self, obj):
        return build_volume_facsimile_url(obj, self.context.get("request"))

    def get_facsimile_name(self, obj):
        return get_facsimile_name(obj)

    def get_facsimile_kind(self, obj):
        return get_facsimile_kind(obj)


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
    volume_facsimile_url = serializers.SerializerMethodField()
    volume_facsimile_name = serializers.SerializerMethodField()
    volume_facsimile_kind = serializers.SerializerMethodField()

    class Meta:
        model = Work
        fields = "__all__"

    def get_date(self, obj):
        return format_work_date(obj)

    def get_volume_facsimile_url(self, obj):
        return build_volume_facsimile_url(obj.volume, self.context.get("request"))

    def get_volume_facsimile_name(self, obj):
        return get_facsimile_name(obj.volume)

    def get_volume_facsimile_kind(self, obj):
        return get_facsimile_kind(obj.volume)


def format_work_date(work):
    if work.date_from and work.date_to and work.date_from != work.date_to:
        return f"{work.date_from}-{work.date_to}"

    return work.date_from or work.date_to


def build_volume_facsimile_url(volume, request=None):
    if not volume.facsimile_file:
        return ""

    path = f"/api/volumes/{volume.id}/facsimile-file/"

    if request:
        return request.build_absolute_uri(path)

    return path


def get_facsimile_name(volume):
    if not volume.facsimile_file:
        return ""

    return volume.facsimile_file.name.rsplit("/", 1)[-1]


def get_facsimile_kind(volume):
    name = get_facsimile_name(volume).lower()

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
    class Meta:
        model = SentimentAnalysisRun
        fields = "__all__"
