import uuid

from django.db import models

from shared.utils.models import GrowingTable


class NatTeamCategories(models.TextChoices):
    FIRST = "FST", "First team"
    U22 = "U22", "Under-22"
    U21 = "U21", "Under-21"
    U19 = "U19", "Under-19"
    U17 = "U17", "Under-17"


class NatTeam(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    federation = models.ForeignKey(
        "volley.federation",
        on_delete=models.CASCADE,
        db_column="federation_id",
        related_name="national_teams",
    )

    category = models.CharField(max_length=3, choices=NatTeamCategories.choices, default=NatTeamCategories.FIRST)

    class Meta:
        db_table = "national_team"
        verbose_name = "National team"
        verbose_name_plural = "National teams"
        constraints = [
            models.UniqueConstraint(
                fields=["federation_id", "category"],
                name="unq_national_team__federation_category",
            )
        ]

    # def __str__(self):
    #     return f"{self.federation.country}"


class AthleteNatPresence(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        "volley.athlete",
        on_delete=models.CASCADE,
        db_column="athlete_id",
        related_name="called_for_national_team",
    )
    national_team = models.ForeignKey(
        "volley.national_team",
        on_delete=models.CASCADE,
        db_column="national_team_id",
        related_name="athletes_called",
    )

    first_callup_date = models.DateField(blank=True, null=True, help_text="only nullable for MVP")
    last_callup_date = models.DateField(blank=True, null=True, help_text="only nullable for MVP")

    class Meta:
        db_table = "athlete_national_team_presence"
        verbose_name = "Athlete calls for national teams"
        verbose_name_plural = "Athletes calls for national teams"
        constraints = [
            models.UniqueConstraint(
                # NOTE: this constraint will fall once callups historic tables are established
                name="unq_athlete_national_team_presence",
                fields=["athlete_id", "national_team_id"],
            ),
            models.CheckConstraint(
                name="chk_ath_nt_presence__dates",
                condition=(models.Q(first_callup_date__isnull=True) | models.Q(last_callup_date__isnull=True) | models.Q(last_callup_date__gte=models.F("first_callup_date"))),
            ),
        ]
