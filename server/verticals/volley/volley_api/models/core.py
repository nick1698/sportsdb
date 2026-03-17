import uuid

from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator

from shared.utils.models import ContractEndReason, GrowingTable

# region CLUB


class Club(GrowingTable):
    id = models.UUIDField(
        primary_key=True, help_text="Not generated: logical hard-ref to platform.org"
    )
    acronym = models.CharField(max_length=8)
    short_name = models.CharField(max_length=64)
    official_name = models.CharField(max_length=256)

    federation = models.ForeignKey(
        "volley.federation",
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


class ClubTeamCategories(models.TextChoices):
    FIRST = "FST", "First team"
    U23 = "U23", "Under-23"
    U21 = "U21", "Under-21"
    U20 = "U20", "Under-20"
    U19 = "U19", "Under-19"
    U17 = "U17", "Under-17"


class ClubTeam(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    club = models.ForeignKey(
        "volley.club",
        on_delete=models.CASCADE,
        db_column="club_id",
        related_name="teams",
    )
    category = models.CharField(
        max_length=3,
        choices=ClubTeamCategories.choices,
        default=ClubTeamCategories.FIRST,
    )

    class Meta:
        db_table = "club_team"
        constraints = [
            models.UniqueConstraint(
                name="unq_club_team__club_category",
                fields=["club_id", "category"],
            )
        ]


class ClubTeamSeason(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    club_team = models.ForeignKey(
        "volley.club_team",
        on_delete=models.CASCADE,
        db_column="club_team_id",
        related_name="seasons",
    )
    season = models.ForeignKey(
        "volley.season",
        on_delete=models.PROTECT,
        db_column="season_id",
        related_name="club_teams",
    )

    class Meta:
        db_table = "club_team_season"
        constraints = [
            models.UniqueConstraint(
                name="unq_club_team_season",
                fields=["club_team_id", "season_id"],
            )
        ]


# endregion

# region ATHLETE


class Hand(models.IntegerChoices):
    RIGHT = 1, "R"
    LEFT = 2, "L"
    AMBI = 3, "A"


class PlayerRole(models.TextChoices):
    SETTER = "SET", "Setter"
    OUTSIDE_HITTER = "OH", "Outside Hitter"
    MIDDLE_BLOCKER = "MB", "Middle Blocker"
    OPPOSITE_HITTER = "OP", "Opposite Hitter"
    LIBERO = "LIB", "Libero"
    DEFENSIVE_SPECIALIST = "DS", "Defensive Specialist"


class Athlete(GrowingTable):
    id = models.UUIDField(
        primary_key=True, help_text="Not generated: logical hard-ref to platform.org"
    )
    dominant_hand = models.SmallIntegerField(choices=Hand.choices, default=Hand.RIGHT)
    primary_role = models.CharField(max_length=4, choices=PlayerRole.choices)
    secondary_role = models.CharField(
        max_length=4, choices=PlayerRole.choices, blank=True, null=True
    )
    # senior team debut date? when is a career starting?
    career_start_date = models.DateField(
        blank=True, null=True
    )  # TODO: only nullable for MVP
    retirement_date = models.DateField(blank=True, null=True)
    jersey_nr_default = models.SmallIntegerField(
        blank=True,
        null=True,
        verbose_name="Preferred jersey nr",
        validators=[MinValueValidator(1)],
    )

    class Meta:
        db_table = "athlete"
        constraints = [
            models.CheckConstraint(
                name="chk_athlete__secondary_role_diff",
                condition=(
                    models.Q(secondary_role__isnull=True)
                    | ~models.Q(secondary_role=models.F("primary_role"))
                ),
            ),
            models.CheckConstraint(
                name="chk_athlete__retired_after_start",
                condition=(
                    models.Q(career_start_date__isnull=True)
                    | models.Q(retirement_date__isnull=True)
                    | models.Q(retirement_date__gte=models.F("career_start_date"))
                ),
            ),
        ]

    def __str__(self):
        return self.short_name


class AthleteClubContract(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete = models.ForeignKey(
        "volley.athlete",
        on_delete=models.CASCADE,
        db_column="athlete_id",
        related_name="contracts_with_clubs",
    )
    club = models.ForeignKey(
        "volley.club",
        on_delete=models.CASCADE,
        db_column="club_id",
        related_name="contracts_with_athletes",
    )

    date_from = models.DateField(blank=True, null=True)  # only nullable for MVP
    date_to = models.DateField(blank=True, null=True)  # only nullable for MVP
    end_reason = models.IntegerField(
        choices=ContractEndReason.choices, blank=True, null=True
    )

    loan_from_club = models.ForeignKey(
        "volley.club",
        on_delete=models.PROTECT,
        db_column="loan_from_club_id",
        related_name="loans",
        blank=True,
        null=True,
        help_text="NOTE: if not null, the contract is a loan from this club",
    )

    class Meta:
        db_table = "athlete_club_contract"
        verbose_name = "Athlete-Club contract"
        constraints = [
            models.CheckConstraint(
                name="chk_ath_club_ctr__dates",
                condition=(
                    models.Q(date_from__isnull=True)
                    | models.Q(date_to__isnull=True)
                    | models.Q(date_to__gte=models.F("date_from"))
                ),
            ),
            models.CheckConstraint(
                name="ck_ath_club_ctr__loan_from_diff",
                condition=(
                    models.Q(loan_from_club_id__isnull=True)
                    | ~models.Q(loan_from_club=models.F("club"))
                ),
            ),
            models.CheckConstraint(
                name="chk_ath_club_ctr__ended",
                condition=(
                    models.Q(date_to__isnull=True) | models.Q(end_reason__gte=0)
                ),
            ),
        ]
        indexes = [
            models.Index(name="idx_ath_club_ctr__athlete", fields=["athlete_id"]),
            models.Index(name="idx_ath_club_ctr__club", fields=["club_id"]),
        ]


class ClubTeamSeasonAthlete(GrowingTable):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    athlete_club_contract = models.ForeignKey(
        "volley.athlete_club_contract",
        on_delete=models.CASCADE,
        db_column="athlete_club_contract_id",
        related_name="seasons",
    )
    club_team_season = models.ForeignKey(
        "volley.club_team_season",
        on_delete=models.CASCADE,
        db_column="club_team_season_id",
        related_name="athletes",
    )
    jersey_nr = models.IntegerField(  # only nullable for MVP
        blank=True, null=True, validators=[MinValueValidator(0), MaxValueValidator[100]]
    )

    class Meta:
        db_table = "club_team_season_athlete"
        constraints = [
            models.UniqueConstraint(
                name="unq_athlete_club_team_season",
                fields=["athlete_club_contract_id", "club_team_season_id"],
            ),
            models.CheckConstraint(
                name="chk_athlete_club_team_season__jersey_nr",
                condition=(
                    models.Q(jersey_nr__isnull=True) | models.Q(jersey_nr__gte=0)
                ),
            ),
        ]


# endregion
