from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

class Command(BaseCommand):
    help = "Reset PostgreSQL sequences for all models in the project"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            for model in apps.get_models():
                table_name = model._meta.db_table
                pk_field = model._meta.pk
                if pk_field.auto_created:  # Only reset auto-increment PKs
                    sequence_name = f"{table_name}_{pk_field.column}_seq"
                    cursor.execute(
                        f"SELECT setval('{sequence_name}', COALESCE((SELECT MAX({pk_field.column}) FROM {table_name}), 0))"
                    )
                    self.stdout.write(self.style.SUCCESS(f"Reset sequence for {table_name}.{pk_field.column}"))
        self.stdout.write(self.style.SUCCESS("All sequences reset successfully!"))
