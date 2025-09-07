from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from rest_framework.exceptions import PermissionDenied
from accounts.utils import get_user_role

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    is_staff = serializers.BooleanField(default=False)
    is_superuser = serializers.BooleanField(default=False)

    class Meta:
        model = User
        fields = ["username","email","password","password2","first_name","last_name","is_staff","is_superuser"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password":"Passwords do not match."})

        req = self.context.get("request")
        if (attrs.get("is_staff") or attrs.get("is_superuser")) and not (req and req.user.is_superuser):
            raise PermissionDenied("Only superusers can make staff/admin users.")
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        is_staff = validated_data.pop("is_staff", False)
        is_superuser = validated_data.pop("is_superuser", False)

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            first_name=validated_data.get("first_name",""),
            last_name=validated_data.get("last_name",""),
            password=validated_data["password"]
        )
        user.is_staff = is_staff
        user.is_superuser = is_superuser
        user.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id","username","email","first_name","last_name","role","is_staff","is_superuser"]
        read_only_fields = ["id","role","is_staff","is_superuser"]

    def get_role(self,obj):
        if not hasattr(obj,"_cached_role"):
            obj._cached_role = get_user_role(obj)
        return obj._cached_role

    def __init__(self, *args, **kwargs):
        super().__init__(*args,**kwargs)
        req = self.context.get("request")
        if req and not req.user.is_superuser:
            self.fields.pop("is_staff",None)
            self.fields.pop("is_superuser",None)

    def update(self, instance, validated_data):
        req = self.context.get("request")
        if req and not req.user.is_superuser:
            validated_data.pop("is_staff",None)
            validated_data.pop("is_superuser",None)
            validated_data.pop("role",None)
        return super().update(instance,validated_data)

    def create(self, validated_data):
        req = self.context.get("request")
        if req and not req.user.is_superuser:
            validated_data.pop("is_staff",None)
            validated_data.pop("is_superuser",None)
            validated_data.pop("role",None)
        return super().create(validated_data)


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id","username","email","role","is_active"]


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True, write_only=True)
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password":"New passwords do not match."})
        return attrs


class AdminResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True, write_only=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_password"]:
            raise serializers.ValidationError({"password":"Passwords do not match."})
        return attrs
