from django.contrib import admin
from shared.utils.admin import GrowingTableAdmin
from platform_api.models import EditRequestsInbox, EditRequestsInboxEvent


class EditRequestsInboxEventInline(admin.TabularInline):
    model = EditRequestsInboxEvent
    extra = 0
    fields = ("event_type", "actor", "notes", "ts_creation")
    readonly_fields = ("ts_creation",)


@admin.register(EditRequestsInbox)
class EditRequestsInboxAdmin(GrowingTableAdmin):
    list_display = (
        "id",
        "entity_type",
        "action",
        "status",
        "sport",
        "target_entity_id",
        "created_by",
        "finalised_by",
        "ts_last_update",
    )
    list_filter = ("status", "entity_type", "action", "sport")
    search_fields = ("id", "target_entity_id", "vertical_entity_id")
    autocomplete_fields = ("sport", "created_by", "finalised_by")
    inlines = [EditRequestsInboxEventInline]

    fieldsets = (
        ("Main", {"fields": ("entity_type", "action", "status")}),
        ("Context", {"fields": ("sport", "vertical_entity_id")}),
        ("Target", {"fields": ("target_entity_id",)}),
        ("Payload", {"fields": ("payload",)}),
        (
            "Audit",
            {
                "fields": (
                    "created_by",
                    "finalised_by",
                    "ts_taken_in_charge",
                    "ts_review_completed",
                    "review_notes",
                )
            },
        ),
    )

    # def save_model(self, request, obj, form, change):
    #     obj.full_clean()
    #     super().save_model(request, obj, form, change)
