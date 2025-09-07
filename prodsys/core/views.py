from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from accounts.utils import get_user_role
from .constants import DASHBOARD_MENU
from accounts.serializers import RegisterSerializer, UserSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from accounts.permissions import ReportPermission

User = get_user_model()


class CoreView(APIView):
    def get(self, request):
        # just a test endpoint
        return Response({"message": "Core endpoint works!"})


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer

    def post(self, request, *args, **kwargs):
        # serializer stuff
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "User registered successfully"}, status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        role = get_user_role(user)
        menu = []
        perms = ReportPermission()

        # go through menu items
        for item in DASHBOARD_MENU:
            # superuser only
            if item.get("superuser_only") and not user.is_superuser:
                continue

            # check custom permission action
            act = item.get("permission_action")
            if act:
                if perms.role_perms.get(role, {}).get(act):
                    menu.append({"name": item["name"], "url": item["url"]})
                continue

            # check codename permission
            code = item.get("permission_codename")
            if code:
                if user.has_perm(f'{item["app_label"]}.{code}'):
                    menu.append({"name": item["name"], "url": item["url"]})
                continue

            # no special perms, just add
            if not act and not code and not item.get("superuser_only"):
                menu.append({"name": item["name"], "url": item["url"]})

        data = {
            "username": user.username,
            "role": role,
            "menu": menu
        }

        return Response(data)


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def update(self, request, *args, **kwargs):
        # messy update method
        u = self.get_object()
        is_staff = request.data.get("is_staff")
        is_superuser = request.data.get("is_superuser")

        if is_superuser is not None:
            if not request.user.is_superuser:
                return Response({"error": "Only superusers can set is_superuser."}, status=403)
            u.is_superuser = is_superuser

        if is_staff is not None:
            u.is_staff = is_staff

        u.save()
        return Response({"message": "User updated successfully."})
