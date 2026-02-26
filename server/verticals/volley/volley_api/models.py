from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=128)
    city = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name
