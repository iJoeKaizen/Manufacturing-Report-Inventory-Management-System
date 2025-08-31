from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ("admin", "Admin"),
        ("manager", "Manager"),
        ("operator", "Operator"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="operator"
    )

    def __str__(self):
        return f"{self.username} ({self.role})"
