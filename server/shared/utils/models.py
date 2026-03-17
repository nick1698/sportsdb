from django.db import models
from django.utils import timezone


class BaseTable(models.Model):
    ts_creation = models.DateTimeField(
        default=timezone.now, editable=False, verbose_name="Created at"
    )
    ts_last_update = models.DateTimeField(auto_now=True, verbose_name="Last updated at")

    class Meta:
        abstract = True


class FixedTable(BaseTable):
    class Meta:
        abstract = True


class GrowingTable(BaseTable):
    class Meta:
        abstract = True


# region COMMON VALUES


class ContractEndReason(models.IntegerChoices):
    """Contract end reason for athletes and staff"""

    EXPIRED = 0, "Expiration"
    TRANSFER = 1, "Transfer"
    RELEASED = 2, "Release"
    TERM = 3, "Mutual termination"
    RETIRED = 5, "Retirement"
    OTHER = 10, "other"
    UNKNOWN = 99, "unknown"


# endregion
