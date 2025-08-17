from django.db import models

class Section(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Machine(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        INACTIVE = "INACTIVE", "Inactive"

    name = models.CharField(max_length=100, unique=True, db_index=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name="machines")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        unique_together = ("name", "section")

    def __str__(self):
        return f"{self.name} ({self.section.name})"
