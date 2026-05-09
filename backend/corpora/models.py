from django.db import models

class Volume(models.Model):
    source_id = models.CharField(max_length=20, blank=True)

    number = models.IntegerField(null=True, blank=True)

    author = models.CharField(max_length=50)
    title_short = models.CharField(max_length=50)
    title = models.CharField(max_length=100)

    xml_file = models.FileField(upload_to="tei_volumes/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Work(models.Model):
    volume = models.ForeignKey(Volume, on_delete=models.CASCADE, related_name="works")

    source_id = models.CharField(max_length=20)
    note = models.CharField(max_length=50, blank=True)
    page_number = models.IntegerField(null=True, blank=True)

    date_from = models.CharField(max_length=20, blank=True)
    date_to = models.CharField(max_length=20, blank=True)
    place = models.CharField(max_length=50, blank=True)

    author = models.CharField(max_length=50)
    language = models.CharField(max_length=20, blank=True)
    title_desc = models.CharField(max_length=200, blank=True)
    title_short = models.CharField(max_length=50, blank=True)
    title = models.CharField(max_length=200)
    genre = models.CharField(max_length=20)

    plain_text = models.TextField()
    raw_xml = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
    
class Token(models.Model):
    work = models.ForeignKey(Work, on_delete=models.CASCADE, related_name="tokens")

    text_position = models.IntegerField(db_index=True)
    text = models.CharField(max_length=20)
    lemma = models.CharField(max_length=20, blank=True, db_index=True)
    pos = models.CharField(max_length=20, blank=True)