from rest_framework import permissions
from reports.models import ProductionReport


class ReportPermission(permissions.BasePermission):
    """
    Centralized role-based access control for ProductionReport.
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

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        role = getattr(user, "role", "OPERATOR")
        action = getattr(view, "action", None)

        # Allow schema generation & browsable API
        if action is None:
            return True

        return self.role_perms.get(role, {}).get(action, False)

    def has_object_permission(self, request, view, obj: ProductionReport):
        user = request.user
        role = getattr(user, "role", "OPERATOR")

        # Operators can only act on their own reports
        if role == "OPERATOR":
            return getattr(obj, "created_by", None) == user

        return True
