from rest_framework import permissions
from accounts.utils import get_user_role


class InventoryPermission(permissions.BasePermission):

    role_perms = {
        "OPERATOR": {
            "list": True, "retrieve": True,
            "create": False, "update": False, "partial_update": False, "delete": False,

            "stock_in": True, "stock_out": True,
            "adjust": False, "transfer": False,
        },
        "SUPERVISOR": {
            "list": True, "retrieve": True,
            "create": False, "update": False, "partial_update": False, "delete": False,

            "stock_in": True, "stock_out": True,
            "adjust": False, "transfer": False,
        },
        "MANAGER": {
            "list": True, "retrieve": True,
            "create": True, "update": True, "partial_update": True, "delete": True,

            "stock_in": True, "stock_out": True,
            "adjust": True, "transfer": True,
        },
        "ADMIN": {
            "list": True, "retrieve": True,
            "create": True, "update": True, "partial_update": True, "delete": True,

            "stock_in": True, "stock_out": True,
            "adjust": True, "transfer": True,
        },
    }

    method_action_map = {
        "get": "list",      
        "put": "update",
        "patch": "partial_update",
        "delete": "delete", 
    }

    def has_permission(self, request, view):
        user = request.user
        if not user.is_authenticated:
            return False

        role = get_user_role(user)

        action = getattr(view, "action", None)

        if action == "destroy":
            action = "delete"

        if action == "retrieve":
            action = "retrieve"

        if not action:
            action = self.method_action_map.get(request.method.lower())

        if action is None:
            return False

        return self.role_perms.get(role, {}).get(action, False)

    def has_object_permission(self, request, view, obj=None):
        return self.has_permission(request, view)
