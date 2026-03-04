from django.contrib import admin
from django.db import models
from django.forms import NumberInput, TextInput


class TimestampAdminMixin:
    readonly_fields = ("ts_creation", "ts_last_update")

    def get_fieldsets(self, request, obj=None):
        fieldsets = list(getattr(self, "fieldsets", ()))

        has_timestamps = any(name == "Timestamps" for name, _ in fieldsets)

        if not has_timestamps:
            fieldsets.append(
                (
                    "Timestamps",
                    {
                        "fields": ("ts_creation", "ts_last_update"),
                        "classes": ("collapse",),
                    },
                )
            )

        return tuple(fieldsets)


class BaseTableAdmin(TimestampAdminMixin, admin.ModelAdmin):
    formfield_overrides = {
        models.TextField: {"widget": TextInput(attrs={"size": 80})},
        models.FloatField: {"widget": NumberInput(attrs={"style": "width: 8em;"})},
    }


class FixedTableAdmin(BaseTableAdmin):
    ordering = ("pk",)


class GrowingTableAdmin(BaseTableAdmin):
    list_per_page = 50
    date_hierarchy = "ts_creation"
