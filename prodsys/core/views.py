from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model

from accounts.serializers import RegisterSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import ReportPermission  # centralized role-based permissions

User = get_user_model()


class CoreView(APIView):
    def get(self, request):
        return Response({"message": "Core endpoint works!"})


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "username": user.username,
            "role": user.role,
        }

        # Role-specific menus
        if user.role == "OPERATOR":
            data["menu"] = [
                {"name": "My Reports", "url": "/reports/my/"},
                {"name": "Submit Report", "url": "/reports/create/"},
            ]
        elif user.role == "SUPERVISOR":
            data["menu"] = [
                {"name": "All Reports", "url": "/reports/"},
                {"name": "Approve Reports", "url": "/reports/approve/"},
            ]
        elif user.role == "MANAGER":
            data["menu"] = [
                {"name": "Reports Overview", "url": "/reports/"},
                {"name": "Manage Inventory", "url": "/inventory/"},
                {"name": "Team Performance", "url": "/performance/"},
            ]
        elif user.role == "ADMIN":
            data["menu"] = [
                {"name": "System Dashboard", "url": "/admin-dashboard/"},
                {"name": "User Management", "url": "/users/"},
                {"name": "Reports", "url": "/reports/"},
                {"name": "Inventory", "url": "/inventory/"},
            ]
        else:
            data["menu"] = []

        return Response(data)


# Role Assignment (Admins only)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [IsAdmin]  # centralized role check

    def update(self, request, *args, **kwargs):
        """
        Admin can update user role.
        """
        partial = kwargs.pop("partial", False)
        instance = self.get_object()

        role = request.data.get("role")
        if role:
            instance.role = role
            instance.save()
            return Response({"message": f"Role updated to {role}"}, status=status.HTTP_200_OK)

        return Response({"error": "Role not provided"}, status=status.HTTP_400_BAD_REQUEST)

