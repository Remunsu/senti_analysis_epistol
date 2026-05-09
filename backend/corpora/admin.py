from django.contrib import admin
from .models import Volume, Work, Token


@admin.register(Volume)
class VolumeAdmin(admin.ModelAdmin):
    list_display = ("id", "number", "title", "author", "uploaded_at")
    search_fields = ("title", "author")


@admin.register(Work)
class WorkAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "genre", "author", "volume")
    list_filter = ("volume", "genre", "language")
    search_fields = ("title", "plain_text")


@admin.register(Token)
class TokenAdmin(admin.ModelAdmin):
    list_display = ("id", "work", "text_position", "text", "lemma", "pos")
    search_fields = ("text", "lemma")
