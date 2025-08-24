from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # Browsable API login/logout (optional, only for DRF UI)
    path("api/auth/", include("rest_framework.urls")),

    # JWT Authentication
    path("api/auth/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # Local apps
    path("api/inventory/", include("inventory.urls")),   # inventory endpoints
    path("api/register/", include("core.urls")),            # core app
    path("api/core/", include("core.urls")), 
    path("api/reports/", include("reports.urls")),       # reports app
    path("api/summary/", include("summary.urls")),       # summary app
]
