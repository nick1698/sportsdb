from django.contrib import admin
from .models import Sport


@admin.register(Sport)
class SportAdmin(admin.ModelAdmin):
    list_display = ("id", "key", "name", "created_at")
    search_fields = ("key", "name")
