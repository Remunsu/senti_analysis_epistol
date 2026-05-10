from django.contrib import admin
from .models import Volume, Work, Token
from .services.tei_parser import parse_volume


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "title", "author", "uploaded_at")
    search_fields = ("title", "author")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        if obj.xml_file and ("xml_file" in form.changed_data or not change):
            parse_volume(obj)


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "genre", "author", "volume")
    list_filter = ("volume", "genre", "language")
    search_fields = ("title", "plain_text")


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("id", "text_position", "text", "lemma", "pos")
    search_fields = ("text", "lemma")