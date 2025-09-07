from rest_framework import permissions, serializers
from django.contrib.auth import get_user_model
from reports.models import ProductionReport
from .utils import get_user_role

User = get_user_model()


class ReportPermission(permissions.BasePermission):
    role_perms = {
        "OPERATOR": {
            "list": True, "retrieve": True, "create": True,
            "update": True, "partial_update": True,
            "approve": False, "delete": False,
            "import_csv": False, "commit_csv": False,
            "preview_csv": False, "download_csv_template": False,
            "export_csv": False,
        },
        "SUPERVISOR": {
            "list": True, "retrieve": True,
            "create": False, "update": False, "partial_update": False,
            "approve": True, "delete": False,
            "import_csv": False, "commit_csv": False,
            "preview_csv": False, "download_csv_template": False,
            "export_csv": True,
        },
        "MANAGER": {
            "list": True, "retrieve": True, "create": True,
            "update": True, "partial_update": True,
            "approve": True, "delete": True,
            "import_csv": True, "commit_csv": True,
            "preview_csv": True, "download_csv_template": True,
            "export_csv": True,
        },
        "ADMIN": {
            "list": True, "retrieve": True, "create": True,
            "update": True, "partial_update": True,
            "approve": True, "delete": True,
            "import_csv": True, "commit_csv": True,
            "preview_csv": True,
            "download_csv_template": True,
            "export_csv": True,
        },
    }

    method_action_map = {
        "get": "list",
        "post": "create",
        "put": "update",
        "patch": "partial_update",
        "delete": "delete",
    }

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        role = get_user_role(user)
        action = getattr(view, "action", None)
        if not action:
            action = self.method_action_map.get(request.method.lower())
        if not action:
            return True

        return self.role_perms.get(role, {}).get(action, False)

    def has_object_permission(self, request, view, obj):
        user = request.user
        role = get_user_role(user)

        if role == "OPERATOR":
            return getattr(obj, "created_by", None) == user

        return True


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "role"]

    def get_role(self, obj):
        return get_user_role(obj)


class IsAdminOrSelf(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if view.action in ["retrieve", "update", "partial_update"]:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        if view.action in ["retrieve", "update", "partial_update"]:
            return obj == user
        return False
