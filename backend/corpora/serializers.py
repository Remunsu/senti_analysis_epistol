from rest_framework import serializers
from .models import Volume, Work


class VolumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Volume
        fields = "__all__"


class WorkListSerializer(serializers.ModelSerializer):
    volume_title = serializers.CharField(source="volume.title", read_only=True)

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