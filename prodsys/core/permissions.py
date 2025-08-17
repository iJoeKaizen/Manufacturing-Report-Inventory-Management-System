from rest_framework.permissions import BasePermission, SAFE_METHODS
from reports.models import ProductionReport

class IsOperator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "OPERATOR"


class IsSupervisor(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["SUPERVISOR", "MANAGER", "ADMIN"]


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["MANAGER", "ADMIN"]


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"


class ReportPermission(BasePermission):
    """
    Role-based object-level rules for ProductionReport.
    """

    def has_object_permission(self, request, view, obj: ProductionReport):
        user = request.user

        # Operators: can only view or edit own reports (not after approval)
        if user.role == "OPERATOR":
            if request.method in SAFE_METHODS:
                return obj.user == user
            if request.method in ["PUT", "PATCH"]:
                return obj.user == user and obj.status != ProductionReport.Status.APPROVED
            if request.method == "DELETE":
                return False
            return False

        # Supervisors: can read all, approve reports
        if user.role == "SUPERVISOR":
            if request.method in SAFE_METHODS:
                return True
            if view.action == "approve":
                return obj.status != ProductionReport.Status.APPROVED
            return False

        # Managers: full CRUD, except cannot edit after approval
        if user.role == "MANAGER":
            if request.method in SAFE_METHODS:
                return True
            if request.method in ["PUT", "PATCH"]:
                return obj.status != ProductionReport.Status.APPROVED
            if request.method == "DELETE":
                return True
            return True

        # Admin: unrestricted
        if user.role == "ADMIN":
            return True

        return False
