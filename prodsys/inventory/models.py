from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Section(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        default_sections = ["Printing", "Slitting", "Sleeving"]
        for name in default_sections:
            cls.objects.get_or_create(name=name)


class Machine(models.Model):
    name = models.CharField(max_length=50, unique=True)
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='machines')

    def __str__(self):
        return self.name

    @classmethod
    def create_defaults(cls):
        """Create default machines linked to sections if they don't exist."""
        # Ensure sections exist first
        Section.create_defaults()
        sections = {s.name: s for s in Section.objects.all()}

        default_machines = [
            ("Flexography", "Printing"),
            ("Rotogravure", "Printing"),
            ("Slitter Rew1", "Slitting"),
            ("Slitter Rew2", "Slitting"),
            ("Sleeving Machine", "Sleeving"),
            ("Sleeve Insp", "Sleeving")
        ]

        for machine_name, section_name in default_machines:
            section = sections.get(section_name)
            if section:
                cls.objects.get_or_create(name=machine_name, section=section)


class ProductionReport(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    job_id = models.CharField(max_length=100, unique=True)
    product_name = models.CharField(max_length=200)
    quantity = models.PositiveIntegerField()
    date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    approved = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='reports_created')

    # Link to Section & Machine
    section = models.ForeignKey(Section, on_delete=models.SET_NULL, null=True, blank=True, related_name='production_reports')
    machine = models.ForeignKey(Machine, on_delete=models.SET_NULL, null=True, blank=True, related_name='production_reports')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.job_id} - {self.product_name}"
