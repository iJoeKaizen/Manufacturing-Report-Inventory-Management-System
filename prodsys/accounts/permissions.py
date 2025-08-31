from rest_framework import permissions, serializers
from django.contrib.auth import get_user_model
from reports.models import ProductionReport

User = get_user_model()


class ReportPermission(permissions.BasePermission):
    """
    Centralized role-based access control for ProductionReport.
    Works with both ViewSets (view.action) and APIViews (request.method).
    """

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
            # Admins unrestricted
            "list": True, "retrieve": True, "create": True,
            "update": True, "partial_update": True,
            "approve": True, "delete": True,
            "import_csv": True, "commit_csv": True,
            "preview_csv": True, "download_csv_template": True,
            "export_csv": True,
        },
    }

    # Map HTTP methods to actions when using APIView
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

        role = getattr(user, "role", "operator").upper()

        # Prefer DRF ViewSet's `action` if available
        action = getattr(view, "action", None)
        if not action:
            # Fallback for APIView
            action = self.method_action_map.get(request.method.lower())

        # Allow schema generation & browsable API
        if action is None:
            return True

        return self.role_perms.get(role, {}).get(action, False)

    def has_object_permission(self, request, view, obj: ProductionReport):
        user = request.user
        role = getattr(user, "role", "operator").upper()

        # Operators can only act on their own reports
        if role == "OPERATOR":
            return getattr(obj, "created_by", None) == user

        return True


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "role")
