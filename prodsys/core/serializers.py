from rest_framework import serializers

class ChoiceFieldSerializer(serializers.Serializer):
    """Generic serializer for dropdown/choice fields."""
    value = serializers.CharField()
    display = serializers.CharField()
