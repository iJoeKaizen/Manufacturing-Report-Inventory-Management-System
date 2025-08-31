# accounts/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for registering a new user.
    """
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email"),
            password=validated_data["password"]
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving/updating user details.
    """
    role = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "is_active")


class AdminUserSerializer(serializers.ModelSerializer):
    """
    Serializer for Admins to manage users (can change role & active status).
    """
    class Meta:
        model = User
        fields = ("id", "username", "email", "role", "is_active")
