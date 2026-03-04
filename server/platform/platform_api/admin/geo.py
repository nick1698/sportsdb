from django.contrib import admin
from django.db import models
from django.forms import TextInput

from platform_api.models import Country, GeoPlace, Venue
from shared.utils.admin import FixedTableAdmin, GrowingTableAdmin


@admin.register(Country)
class CountryAdmin(FixedTableAdmin):
    list_display = ("iso2", "iso3", "numeric_code", "name_en")
    search_fields = ("iso2", "iso3", "name_en", "name_local")
    ordering = ("iso2",)

    fieldsets = (
        (
            "Main info",
            {
                "fields": (
                    ("iso2", "iso3", "numeric_code"),
                    ("name_en", "name_local"),
                ),
            },
        ),
    )


@admin.register(GeoPlace)
class GeoPlaceAdmin(GrowingTableAdmin):
    list_display = ("name", "kind", "country", "parent", "timezone")
    list_filter = ("country", "kind")
    search_fields = ("name", "normalized_name")
    autocomplete_fields = ("parent",)
    ordering = ("country", "kind", "normalized_name")

    fieldsets = (
        (
            "Main info",
            {
                "fields": (
                    ("name", "normalized_name"),
                    "kind",
                    ("country", "parent"),
                    ("lat", "lon", "timezone"),
                )
            },
        ),
    )


@admin.register(Venue)
class VenueAdmin(GrowingTableAdmin):
    list_display = ("name", "short_name", "country", "geo_place", "is_active")
    list_filter = ("country", "is_active")
    search_fields = ("name", "short_name", "address_line", "postal_code")
    autocomplete_fields = ("geo_place",)
    ordering = ("country", "name")

    formfield_overrides = {
        **FixedTableAdmin.formfield_overrides,
        models.TextField: {"widget": TextInput(attrs={"size": 80})},
    }

    fieldsets = (
        (
            "Main info",
            {
                "fields": (
                    ("name", "short_name"),
                    ("capacity", "date_opening"),
                    "is_active",
                )
            },
        ),
        (
            "Geo info",
            {
                "fields": (
                    ("country", "geo_place"),
                    ("lat", "lon"),
                    ("address_line", "postal_code"),
                )
            },
        ),
    )
