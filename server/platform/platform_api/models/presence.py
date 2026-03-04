import uuid

from django.db import models

from shared.utils.models import GrowingTable


class OrgPresence(GrowingTable):
    """
    Mapping Core Org -> Vertical entity (per sport)
    One-to-many: the same Org can be present in many sports
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    org = models.ForeignKey(
        "platform_api.Org", on_delete=models.CASCADE, related_name="presences"
    )
    sport = models.ForeignKey(
        "platform_api.Sport",
        to_field="key",
        db_column="sport_key",
        on_delete=models.PROTECT,
        related_name="org_presences",
    )

    vertical_entity_id = models.UUIDField()

    class Meta:
        db_table = "org_sport_presence"
        verbose_name_plural = "Org-sport "
        constraints = [
            models.UniqueConstraint(
                fields=["org", "sport", "vertical_entity_id"],
                name="uq_os_presence__org_sport_vertical",
            )
        ]
        indexes = [
            models.Index(
                fields=["org", "sport"], name="ix_os_presence__org_sport"
            ),
            models.Index(
                fields=["sport", "vertical_entity_id"],
                name="ix_os_presence__sport_vertical",
            ),
        ]

    def __str__(self):
        return f"OrgPresence(org={self.org_id}, sport={self.sport_id})"


class PersonPresence(GrowingTable):
    """
    Mapping Core Person -> Vertical entity (per sport)
    One-to-many: the same Person can be present in multiple sports and in multiple roles in the same sport
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    person = models.ForeignKey(
        "platform_api.Person", on_delete=models.CASCADE, related_name="presences"
    )
    sport = models.ForeignKey(
        "platform_api.Sport",
        to_field="key",
        db_column="sport_key",
        on_delete=models.PROTECT,
        related_name="person_presences",
    )

    vertical_entity_id = models.UUIDField()

    class Meta:
        db_table = "person_sport_presence"
        constraints = [
            models.UniqueConstraint(
                fields=["person", "sport", "vertical_entity_id"],
                name="uq_ps_presence__person_sport_vertical",
            )
        ]
        indexes = [
            models.Index(
                fields=["person", "sport"],
                name="ix_ps_presence__person_sport",
            ),
            models.Index(
                fields=["sport", "vertical_entity_id"],
                name="ix_ps_presence__sport_vertical",
            ),
        ]

    def __str__(self):
        return f"PersonPresence(person={self.person_id}, sport={self.sport_id})"
