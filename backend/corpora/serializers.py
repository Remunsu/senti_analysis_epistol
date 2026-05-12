from rest_framework import serializers
from .models import SentimentAnalysisResult, SentimentAnalysisRun, SentimentFragmentLabel, Volume, Work


class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = "__all__"


class WorkListSerializer(serializers.ModelSerializer):
    volume_title = serializers.CharField(source="volume.title_short", read_only=True)

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
            "place",
            "language",
            "page_number",
        ]


class WorkDetailSerializer(serializers.ModelSerializer):
    volume_title = serializers.CharField(source="volume.title", read_only=True)

    class Meta:
        model = Work
        fields = "__all__"


class SentimentFragmentLabelSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentFragmentLabel
        fields = "__all__"


class SentimentAnalysisRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = SentimentAnalysisRun
        fields = "__all__"


class SentimentAnalysisResultSerializer(serializers.ModelSerializer):
    work_title = serializers.CharField(source="work.title", read_only=True)
    work_author = serializers.CharField(source="work.author", read_only=True)
    work_date = serializers.CharField(source="work.date", read_only=True)
    work_genre = serializers.CharField(source="work.genre", read_only=True)

    class Meta:
        model = SentimentAnalysisResult
        fields = "__all__"
