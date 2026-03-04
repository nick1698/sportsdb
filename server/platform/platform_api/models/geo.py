import uuid

from django.db import models
from django.db.models import Q

from shared.utils.models import FixedTable


class Country(FixedTable):
    """
    ISO 3166-1 country registry
    """

    iso2 = models.CharField(max_length=2, primary_key=True)
    iso3 = models.CharField(max_length=3, unique=True)
    numeric_code = models.CharField(max_length=3, unique=True)
    name_en = models.CharField(max_length=128, verbose_name="name (eng)")
    name_local = models.CharField(max_length=128, null=True, blank=True, verbose_name="local")

    class Meta:
        db_table = "country"
        verbose_name_plural = "countries"
        indexes = [models.Index(fields=["name_en"], name="idx_country_name_en")]

    def __str__(self) -> str:
        return f"{self.iso2} - {self.name_en}"


# region GEOPLACE


class GeoPlaceKind(models.TextChoices):
    LOCALITY = "locality", "Locality"  # generic
    REGION = "region", "Region"
    STATE = "state", "State"
    PROVINCE = "province", "Province"
    COUNTY = "county", "County"
    MUNICIPALITY = "municipality", "Municipality"
    CITY = "city", "City"
    VILLAGE = "village", "Village"
    DISTRICT = "district", "District"
    NEIGHBORHOOD = "neighborhood", "Neighborhood"

    # TODO: servirà una migrazione manuale quando i valori saranno "definitivi"
    """
    class Migration(migrations.Migration):
        dependencies = [
            ("platform_api", "XXXX_previous_migration"),
        ]

        operations = [
            migrations.RunSQL(
                sql="
                    DO $$
                    BEGIN
                        IF NOT EXISTS (
                            SELECT 1
                            FROM pg_type
                            WHERE typname = 'geo_place_kind'
                        ) THEN
                            CREATE TYPE geo_place_kind AS ENUM (
                                'region',
                                ...
                            );
                        END IF;
                    END
                    $$;

                    ALTER TABLE geo_place
                    ALTER COLUMN kind
                    TYPE geo_place_kind
                    USING kind::geo_place_kind;
                ",
                reverse_sql="
                    ALTER TABLE geo_place
                    ALTER COLUMN kind
                    TYPE text
                    USING kind::text;

                    DROP TYPE IF EXISTS geo_place_kind;
                ",
            ),
        ]
    """


class GeoPlace(FixedTable):
    """
    Region, city, etc.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        db_column="country_id",
        related_name="geo_places",
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="parent_id",
        related_name="children",
        verbose_name="Broader area"
    )

    name = models.CharField(max_length=128)
    normalized_name = models.CharField(max_length=128, unique=True)

    kind = models.CharField(
        max_length=20, choices=GeoPlaceKind.choices, default=GeoPlaceKind.LOCALITY.value
    )

    lat = models.FloatField(
        null=True, blank=True, verbose_name="Latitude"
    )  # NOTE: only nullable for MVP
    lon = models.FloatField(
        null=True, blank=True, verbose_name="Longitude"
    )  # NOTE: only nullable for MVP
    timezone = models.CharField(max_length=8, null=True, blank=True)  # NOTE: only nullable for MVP

    class Meta:
        db_table = "geo_place"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(lat__isnull=True) & Q(lon__isnull=True))
                    | (Q(lat__isnull=False) & Q(lon__isnull=False))
                ),
                name="chk_geo_place_latlon",
            ),
            models.UniqueConstraint(
                fields=["country", "parent", "kind", "normalized_name"],
                condition=(Q(kind__isnull=False) & Q(normalized_name__isnull=False)),
                name="unq_geo_place_country_parent_kind_normname",
            ),
        ]
        indexes = [
            # idx_geo_place_search ON (country_id, kind, normalized_name)
            models.Index(
                fields=["country", "kind", "normalized_name"],
                name="idx_geo_place_search",
            ),
        ]

    def __str__(self):
        return self.name


# endregion


class Venue(FixedTable):
    """
    Physical place used in sport
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=256)
    short_name = models.CharField(max_length=128, null=True, blank=True)

    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, db_column="country_id", related_name="venues"
    )
    geo_place = models.ForeignKey(
        GeoPlace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="geo_place_id",
        related_name="venues",
        verbose_name="location"
    )  # NOTE: only nullable for MVP

    address_line = models.TextField(
        null=True, blank=True
    )  # NOTE: only nullable for MVP
    postal_code = models.CharField(
        max_length=16, null=True, blank=True
    )  # NOTE: only nullable for MVP

    lat = models.FloatField(null=True, blank=True)  # NOTE: only nullable for MVP
    lon = models.FloatField(null=True, blank=True)  # NOTE: only nullable for MVP

    capacity = models.IntegerField(null=True, blank=True)  # NOTE: only nullable for MVP
    date_opening = models.DateField(
        null=True, blank=True
    )  # NOTE: only nullable for MVP
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "venue"
        constraints = [
            models.CheckConstraint(
                condition=(
                    (Q(lat__isnull=True) & Q(lon__isnull=True))
                    | (Q(lat__isnull=False) & Q(lon__isnull=False))
                ),
                name="chk_venue_latlon",
            ),
        ]
        indexes = [
            models.Index(
                fields=["country", "geo_place"], name="idx_venue_country_geoplace"
            ),
        ]

    def __str__(self):
        return self.short_name or self.name
