from django.db import models

class Volume(models.Model):
    source_id = models.CharField(max_length=20, blank=True)

    number = models.IntegerField(null=True, blank=True)

    author = models.CharField(max_length=50, blank=True)
    title_short = models.CharField(max_length=100, blank=True)
    title = models.CharField(max_length=200, blank=True)

    xml_file = models.FileField(upload_to="tei_volumes/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Work(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, related_name="works")

    source_id = models.CharField(max_length=20)
    note = models.CharField(max_length=50, blank=True)
    page_number = models.IntegerField(null=True, blank=True)

    date = models.CharField(max_length=20, blank=True)
    place = models.CharField(max_length=50, blank=True)

    author = models.CharField(max_length=50, blank=True)
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
    
class Token(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="tokens")

    text_position = models.IntegerField(db_index=True)
    text = models.CharField(max_length=20, blank=True)
    lemma = models.CharField(max_length=20, blank=True, db_index=True)
    pos = models.CharField(max_length=20, blank=True)


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
