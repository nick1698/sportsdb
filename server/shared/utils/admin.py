from django.contrib import admin


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
    pass


class FixedTableAdmin(BaseTableAdmin):
    ordering = ("pk",)


class GrowingTableAdmin(BaseTableAdmin):
    list_per_page = 50
    date_hierarchy = "ts_creation"
