from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = (
        ("OPERATOR", "Operator"),
        ("SUPERVISOR", "Supervisor"),
        ("MANAGER", "Manager"),
        ("ADMIN", "Admin"),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="OPERATOR")
