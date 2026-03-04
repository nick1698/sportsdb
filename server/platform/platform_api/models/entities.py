import uuid

from django.db import models
from django.db.models import Q, F

from shared.utils.models import GrowingTable
from .geo import Country, GeoPlace


class Sport(GrowingTable):
    key = models.CharField(primary_key=True, max_length=64)  # immutable slug
    name_en = models.CharField(max_length=128)  # display label (can evolve, key should not)
    description = models.TextField(
        null=True, blank=True, verbose_name="Brief description"
    )
    rules = models.TextField(
        null=True, blank=True, verbose_name="NOTE: preferably in English"
    )

    class Meta:
        db_table = "sport"
        indexes = [models.Index(fields=["name_en"], name="idx_sport_name_en")]

    def __str__(self):
        return self.name_en


# region ORG


class OrgType(models.IntegerChoices):
    NATION = 1, "nation"
    CLUB = 2, "club"
    # TODO: servirà una migrazione manuale quando i valori saranno "definitivi" (vedi GeoPlaceKind)


class Org(GrowingTable):
    """
    Cross-sport organization (nations or clubs)
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    type = models.SmallIntegerField(
        choices=OrgType.choices, default=OrgType.NATION.value
    )
    name = models.CharField(max_length=128)
    short_name = models.CharField(max_length=64)
    date_foundation = models.DateField(
        null=True, blank=True
    )  # NOTE: only nullable for MVP

    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, db_column="country_id", related_name="orgs"
    )
    home_geo_place = models.ForeignKey(
        GeoPlace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="home_geo_place_id",
        related_name="orgs_home",
    )  # NOTE: only nullable for MVP

    website = models.CharField(max_length=256, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "org"
        indexes = [models.Index(fields=["country"], name="idx_org_country")]

    def __str__(self):
        return self.short_name or self.name


# endregion


class Sex(models.IntegerChoices):
    FEMALE = 1, "female"
    MALE = 2, "male"
    OTHER = 3, "other"  # NOTE: meaning it's not relevant (e.g. not for athletes)
    # TODO: servirà una migrazione manuale quando i valori saranno "definitivi" (vedi GeoPlaceKind)


class Person(GrowingTable):
    """
    Cross-sport unique person identification
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    given_name = models.CharField(max_length=128)
    family_name = models.CharField(max_length=128)
    nickname = models.CharField(max_length=128, null=True, blank=True)

    sex = models.SmallIntegerField(choices=Sex.choices)

    birth_date = models.DateField(null=True, blank=True)  # NOTE: only nullable for MVP
    birth_place = models.ForeignKey(
        GeoPlace,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="birth_geo_place_id",
        related_name="people_born_in_place",
    )  # NOTE: only nullable for MVP
    death_date = models.DateField(null=True, blank=True)

    primary_nationality = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        db_column="primary_nationality_id",
        related_name="people_primary_nat",
    )
    sporting_nationality = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="sporting_nationality_id",
        related_name="people_sporting_nat",
    )

    class Meta:
        db_table = "person"
        verbose_name_plural = "people"
        constraints = [
            models.CheckConstraint(
                condition=Q(death_date__isnull=True)
                | Q(birth_date__isnull=True)
                | Q(death_date__gte=F("birth_date")),
                name="chk_person_death_after_birth",
            ),
        ]
        indexes = [
            models.Index(
                fields=["family_name", "given_name"], name="idx_person_full_name"
            ),
            models.Index(fields=["primary_nationality"], name="idx_person_primary_nat"),
        ]

    @property
    def full_name(self):
        return f"{self.given_name} {self.family_name}".strip()

    def __str__(self):
        return self.nickname or self.full_name
