# import uuid

from django.db import models

from shared.utils.models import GrowingTable
from .governance import Federation

# region CLUB


class Club(GrowingTable):
    id = models.UUIDField(
        primary_key=True, help_text="Not generated: logical hard-ref to platform.org"
    )
    acronym = models.CharField(max_length=8)
    short_name = models.CharField(max_length=64)
    official_name = models.CharField(max_length=256)

    federation = models.ForeignKey(
        Federation,
        on_delete=models.PROTECT,
        db_column="federation_id",
        related_name="clubs",
    )

    date_foundation = models.DateField(
        null=True, blank=True, help_text="Volley section foundation"
    )  # NOTE: only nullable for MVP
    # no website: see the Org website

    class Meta:
        db_table = "club"

    def __str__(self):
        return self.short_name


# endregion

# region ATHLETE


class Hand(models.IntegerChoices):
    RIGHT = 1, "R"
    LEFT = 2, "L"
    AMBI = 3, "A"


class PlayerRole(models.TextChoices):
    SETTER = 'SET', 'Setter'
    OUTSIDE_HITTER = 'OH', 'Outside Hitter'
    MIDDLE_BLOCKER = 'MB', 'Middle Blocker'
    OPPOSITE_HITTER = 'OP', 'Opposite Hitter'
    LIBERO = 'LIB', 'Libero'
    DEFENSIVE_SPECIALIST = 'DS', 'Defensive Specialist'


class Athlete(GrowingTable):
    id = models.UUIDField(
        primary_key=True, help_text="Not generated: logical hard-ref to platform.org"
    )
    dominant_hand = models.SmallIntegerField(choices=Hand.choices, default=Hand.RIGHT)
    primary_role = models.CharField(max_length=4, choices=PlayerRole.choices)
    secondary_role = models.CharField(max_length=4, choices=PlayerRole.choices, blank=True, null=True)
    # senior team debut date? when is a career starting?
    career_start_date = models.DateField(blank=True, null=True)  # TODO: only nullable for MVP
    retirement_date = models.DateField(blank=True, null=True)
    jersey_nr_default = models.SmallIntegerField(blank=True, null=True, verbose_name="Preferred jersey nr")

    class Meta:
        db_table = "athlete"

    def __str__(self):
        return self.short_name


# endregion
