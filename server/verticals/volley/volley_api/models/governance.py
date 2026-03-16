import uuid

from django.db import models

from shared.utils.models import FixedTable


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
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    acronym = models.CharField(max_length=16)
    official_name = models.CharField(max_length=256)
    name_en = models.CharField(max_length=256, blank=True, null=True)

    confederation = models.ForeignKey(
        Confederation,
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
