from rest_framework import serializers
from .models import Section, Machine

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'name']


class MachineSerializer(serializers.ModelSerializer):
    section = SectionSerializer(read_only=True)
    section_id = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(), source='section', write_only=True
    )

    class Meta:
        model = Machine
        fields = ['id', 'name', 'section', 'section_id']
