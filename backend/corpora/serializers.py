from rest_framework import serializers
from .models import SentimentAnalysisRun, SentimentFragmentLabel, Volume, Work


class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = "__all__"


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

    class Meta:
        model = Work
        fields = "__all__"

    def get_date(self, obj):
        return format_work_date(obj)


def format_work_date(work):
    if work.date_from and work.date_to and work.date_from != work.date_to:
        return f"{work.date_from}-{work.date_to}"

    return work.date_from or work.date_to


class SentimentFragmentLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentFragmentLabel
        fields = "__all__"


class SentimentAnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentAnalysisRun
        fields = "__all__"
