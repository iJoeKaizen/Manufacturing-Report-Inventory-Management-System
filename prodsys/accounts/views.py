from rest_framework import generics, viewsets, status, permissions, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework_simplejwt.tokens import RefreshToken
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from .serializers import RegisterSerializer, UserSerializer, AdminUserSerializer, ChangePasswordSerializer, AdminResetPasswordSerializer
from .utils import get_user_role

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh = request.data["refresh"]
            token = RefreshToken(refresh)
            token.blacklist()
            return Response({"message":"Logged out"}, status=205)
        except:
            return Response({"error":"bad token"}, status=400)


class IsAdminOrSelf(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_superuser:
            return True
        if view.action in ["retrieve","update","partial_update"]:
            return True
        return False
    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_superuser:
            return True
        if view.action in ["retrieve","update","partial_update"]:
            return obj == user
        return False


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsAdminOrSelf]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["is_active","is_staff","is_superuser"]
    search_fields = ["username","email","first_name","last_name"]
    ordering_fields = ["id","username","email","date_joined"]
    ordering = ["id"]

    def get_serializer_class(self):
        if self.request.user.is_staff or self.request.user.is_superuser:
            return AdminUserSerializer
        return UserSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return User.objects.all()
        return User.objects.filter(id=user.id)

    def update(self, request, *args, **kwargs):
        inst = self.get_object()
        if not request.user.is_superuser:
            for f in ["role","is_staff","is_superuser"]:
                if f in request.data:
                    return Response({"error":"cannot change "+f}, status=403)
        return super().update(request,*args,**kwargs)

    @action(detail=False, methods=["get","put","patch"], url_path="me")
    def me(self, request):
        part = request.method=="PATCH"
        ser = self.get_serializer(request.user, data=request.data, partial=part)
        if request.method in ["PUT","PATCH"]:
            if not request.user.is_superuser:
                for f in ["role","is_staff","is_superuser"]:
                    if f in request.data:
                        return Response({"error":"cannot change "+f}, status=403)
            ser.is_valid(raise_exception=True)
            ser.save()
        return Response(ser.data)


class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]
    def get_object(self):
        return self.request.user
    def update(self, request, *args, **kwargs):
        user = self.get_object()
        ser = self.get_serializer(data=request.data)
        ser.is_valid(raise_exception=True)
        if not user.check_password(ser.validated_data["old_password"]):
            return Response({"old_password":"wrong"}, status=400)
        user.set_password(ser.validated_data["new_password"])
        user.save()
        return Response({"message":"password changed"}, status=200)


class AdminResetPasswordView(APIView):
    permission_classes = [permissions.IsAdminUser]
    def post(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except:
            return Response({"error":"user not found"}, status=404)
        ser = AdminResetPasswordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user.set_password(ser.validated_data["new_password"])
        user.save()
        return Response({"message":"password reset"}, status=200)
