import uuid

from django.db import models

from shared.utils.models import FixedTable, GrowingTable


class Confederation(FixedTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    acronym = models.CharField(max_length=16)
    name_local = models.CharField(max_length=256)
    name_en = models.CharField(max_length=256, blank=True, null=True)

    date_foundation = models.DateField(
        null=True, blank=True
    )  # NOTE: only nullable for MVP
    website = models.URLField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = "confederation"

    def __str__(self):
        return self.acronym


class Federation(FixedTable):
    id = models.UUIDField(
        primary_key=True, help_text="Not generated: logical hard-ref to platform.org"
    )
    acronym = models.CharField(max_length=16)
    official_name = models.CharField(max_length=256)
    name_en = models.CharField(max_length=256, blank=True, null=True)

    confederation = models.ForeignKey(
        "volley.confederation",
        on_delete=models.PROTECT,
        db_column="confederation_id",
        related_name="federations",
    )

    date_foundation = models.DateField(
        null=True, blank=True
    )  # NOTE: only nullable for MVP
    website = models.URLField(max_length=256, null=True, blank=True)

    class Meta:
        db_table = "federation"

    def __str__(self):
        return self.acronym


class Season(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        db_table = "season"
        constraints = [
            models.CheckConstraint(
                name="chk_season__dates",
                condition=(models.Q(end_date__gte=models.F("start_date"))),
            ),
        ]

    def __str__(self):
        # TODO: review this
        return f"{self.start_date.year}-{self.end_date.year-2000}"


# region COMPETITION


class CompetitionScope(models.IntegerChoices):
    INTERNATIONAL = 0, "International"
    NATIONAL = 1, "National"
    # LOCAL = 2, 'Local'


class CompetitionType(models.TextChoices):
    LEAGUE = "leag", "League"
    CUP = "cup", "Cup"
    TOURNAMENT = "trnt", "Tournament"
    FRIENDLY = "frly", "Friendly"
    QUALIFIER = "qual", "Qualifier"


class Competition(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    scope = models.SmallIntegerField(
        choices=CompetitionScope.choices, default=CompetitionScope.NATIONAL
    )
    type = models.CharField(
        max_length=4, choices=CompetitionType.choices, default=CompetitionType.LEAGUE
    )
    organizer_id = models.UUIDField(
        help_text="No foreign key: logical hard-ref to a volley organizer"
    )

    official_name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=255)
    acronym = models.CharField(max_length=16, blank=True, null=True)

    level = models.IntegerField(
        help_text="from 1 to 99 = senior teams; from 100 to 199 = youth teams; from 200 = amateur teams"
    )
    date_foundation = models.DateField(blank=True, null=True)  # only nullable per MVP

    class Meta:
        db_table = "competition"
        constraints = [
            # models.CheckConstraint(
            #     name="chk_competition_scope",
            #     condition=models.Q(scope__in=CompetitionScope.values),
            # ),
            models.UniqueConstraint(
                name="unq_competition_official_name",
                fields=["organizer_id", "official_name"],
            ),
            models.UniqueConstraint(
                name="unq_competition__type_level",
                fields=["scope", "organizer_id", "type", "level"],
            ),
        ]

    def __str__(self):
        return f"{self.official_name} ({self.acronym or ''})".strip()


# endregion
