from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        OPERATOR = "OPERATOR", "Operator"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        MANAGER = "MANAGER", "Manager"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.OPERATOR,
        db_index=True,
    )

    # Override groups and permissions to avoid clashes
    groups = models.ManyToManyField(
        "auth.Group",
        related_name="custom_users",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )
    user_permissions = models.ManyToManyField(
        "auth.Permission",
        related_name="custom_users_permissions",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    class Meta:
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.username} ({self.role})"
