from django.contrib import admin
from django.db import models
from django.forms import NumberInput


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
        models.FloatField: {"widget": NumberInput(attrs={"style": "width: 6em;"})},
    }

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)

        if isinstance(db_field, models.CharField) and formfield:
            max_len = db_field.max_length or 20
            formfield.widget.attrs["style"] = f"width: {min(max_len, 60)}ch;"

        return formfield


class FixedTableAdmin(BaseTableAdmin):
    ordering = ("pk",)


class GrowingTableAdmin(BaseTableAdmin):
    list_per_page = 50
    date_hierarchy = "ts_creation"
