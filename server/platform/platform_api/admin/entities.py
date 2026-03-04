from django.contrib import admin

from platform_api.models import Sport, Org, Person, OrgPresence, PersonPresence
from shared.utils.admin import GrowingTableAdmin


@admin.register(Sport)
class SportAdmin(GrowingTableAdmin):
    list_display = ("key", "name_en")
    search_fields = ("key", "name_en")
    ordering = ("key",)

    fieldsets = (
        (
            "Main info",
            {"fields": ("key", "name_en", "description", "rules")},
        ),
    )


# region ORG


class OrgPresenceInline(admin.TabularInline):
    model = OrgPresence
    extra = 0
    autocomplete_fields = ("sport",)
    fields = (
        "sport",
        "vertical_entity_id",
        "ts_last_update",
    )
    readonly_fields = ("ts_creation", "ts_last_update")


@admin.register(Org)
class OrgAdmin(GrowingTableAdmin):
    list_display = ("short_name", "name", "type", "country", "is_active")
    list_filter = ("type", "country", "is_active")
    search_fields = ("name", "short_name")
    autocomplete_fields = ("home_geo_place",)
    ordering = ("country", "type", "short_name")
    inlines = [OrgPresenceInline]

    fieldsets = (
        (
            "Main info",
            {
                "fields": (
                    "type",
                    "name",
                    "short_name",
                    ("country", "home_geo_place", "date_foundation"),
                    "website",
                    "is_active",
                )
            },
        ),
    )


# endregion ORG

# region PERSON


class PersonPresenceInline(admin.TabularInline):
    model = PersonPresence
    extra = 0
    autocomplete_fields = ("sport",)
    fields = (
        "sport",
        "vertical_entity_id",
        "ts_last_update",
    )
    readonly_fields = ("ts_creation", "ts_last_update")


@admin.register(Person)
class PersonAdmin(GrowingTableAdmin):
    list_display = (
        "full_name",
        "sex",
        "primary_nationality",
        "birth_date",
    )
    list_filter = ("sex", "primary_nationality")
    search_fields = ("family_name", "given_name", "nickname")
    autocomplete_fields = ("birth_place",)
    ordering = ("family_name", "given_name")
    inlines = [PersonPresenceInline]

    fieldsets = (
        (
            "Main info",
            {
                "fields": (
                    ("given_name", "family_name"),
                    "nickname",
                    "sex",
                    ("birth_date", "birth_place", "death_date"),
                    ("primary_nationality", "sporting_nationality"),
                )
            },
        ),
    )


# endregion PERSON
