from rest_framework import serializers

class ChoiceFieldSerializer(serializers.Serializer):
    value = serializers.CharField()
    display = serializers.CharField()
