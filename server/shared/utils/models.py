from django.db import models
from django.utils import timezone


class BaseTable(models.Model):
    ts_creation = models.DateTimeField(default=timezone.now, editable=False, verbose_name="Created at")
    ts_last_update = models.DateTimeField(auto_now=True, verbose_name="Last updated at")

    class Meta:
        abstract = True


class FixedTable(BaseTable):
    class Meta:
        abstract = True


class GrowingTable(BaseTable):
    class Meta:
        abstract = True
