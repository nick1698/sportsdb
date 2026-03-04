from django.contrib import admin

from platform_api.models import Sport, Org, Person
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


@admin.register(Org)
class OrgAdmin(GrowingTableAdmin):
    list_display = ("short_name", "name", "type", "country", "is_active")
    list_filter = ("type", "country", "is_active")
    search_fields = ("name", "short_name")
    autocomplete_fields = ("home_geo_place",)
    ordering = ("country", "type", "short_name")

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


@admin.register(Person)
class PersonAdmin(admin.ModelAdmin):
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
