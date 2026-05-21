from django.conf import settings
from django.db import models

class Volume(models.Model):
    source_id = models.CharField(max_length=20, blank=True)

    number = models.IntegerField(null=True, blank=True)

    author = models.CharField(max_length=50, blank=True)
    title_short = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200, blank=True)

    xml_file = models.FileField(upload_to="tei_volumes/")
    facsimile_file = models.FileField(upload_to="volume_facsimiles/", blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Work(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, related_name="works")

    source_id = models.CharField(max_length=20)
    note = models.CharField(max_length=50, blank=True)
    number = models.IntegerField(null=True, blank=True)

    date_from = models.CharField(max_length=100, blank=True)
    date_to = models.CharField(max_length=100, blank=True)
    place = models.CharField(max_length=50, blank=True)
    pages = models.CharField(max_length=50, blank=True)

    author = models.CharField(max_length=50, blank=True)
    recipient = models.CharField(max_length=200, blank=True)
    language = models.CharField(max_length=20, blank=True)
    title_desc = models.CharField(max_length=200, blank=True)
    title_short = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200, blank=True)
    genre = models.CharField(max_length=20, blank=True)

    plain_text = models.TextField(blank=True)
    raw_xml = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class SentimentFragmentLabel(models.Model):
    LABEL_CHOICES = [
        ("-1", "Негативная"),
        ("0", "Нейтральная"),
        ("1", "Позитивная"),
    ]

    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="sentiment_labels")

    segment_index = models.IntegerField()
    word_start = models.IntegerField()
    word_end = models.IntegerField()
    text = models.TextField()

    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("work", "segment_index")
        ordering = ["work", "segment_index"]


class SentimentAnnotationSkip(models.Model):
    work = models.OneToOneField(
        Work,
        on_delete=models.CASCADE,
        related_name="sentiment_annotation_skip",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["work"]


class SentimentAnalysisRun(models.Model):
    MODEL_KIND_CHOICES = [
        ("rubert", "RuBERT"),
    ]
    STATUS_CHOICES = [
        ("running", "Выполняется"),
        ("completed", "Завершен"),
        ("failed", "Ошибка"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sentiment_analysis_runs",
        null=True,
        blank=True,
    )
    model_kind = models.CharField(max_length=20, choices=MODEL_KIND_CHOICES, default="rubert")
    model_name = models.CharField(max_length=200)
    segment_size = models.IntegerField(default=60)
    max_segment_size = models.IntegerField(null=True, blank=True)
    window_step = models.IntegerField(default=0)
    works_count = models.IntegerField(default=0)
    results_count = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="completed")
    error_message = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.model_name} ({self.created_at:%Y-%m-%d %H:%M})"


class SentimentAnalysisResult(models.Model):
    LABEL_CHOICES = SentimentFragmentLabel.LABEL_CHOICES

    run = models.ForeignKey(SentimentAnalysisRun, on_delete=models.CASCADE, related_name="results")
    work = models.ForeignKey(
        Work,
        on_delete=models.SET_NULL,
        related_name="sentiment_results",
        null=True,
        blank=True,
    )
    original_work_id = models.IntegerField(db_index=True)

    snapshot_title = models.CharField(max_length=200, blank=True)
    snapshot_author = models.CharField(max_length=50, blank=True)
    snapshot_recipient = models.CharField(max_length=200, blank=True)
    snapshot_date_from = models.CharField(max_length=100, blank=True)
    snapshot_date_to = models.CharField(max_length=100, blank=True)
    snapshot_genre = models.CharField(max_length=20, blank=True)
    snapshot_place = models.CharField(max_length=50, blank=True)

    segment_index = models.IntegerField()
    word_start = models.IntegerField()
    word_end = models.IntegerField()
    text = models.TextField()

    label = models.CharField(max_length=20, choices=LABEL_CHOICES)
    confidence = models.FloatField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("run", "original_work_id", "segment_index")
        ordering = ["run", "original_work_id", "segment_index"]
