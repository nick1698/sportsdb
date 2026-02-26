from django.db import models


class Sport(models.Model):
    key = models.SlugField(max_length=32, unique=True)
    name = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.key} ({self.name})"
