from django.contrib import admin
from .models import Machine, Section

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]  # Required for autocomplete_fields

@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["name"]
    search_fields = ["name"]  # Required for autocomplete_fields
