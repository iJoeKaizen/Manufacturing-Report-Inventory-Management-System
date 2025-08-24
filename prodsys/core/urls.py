from django.urls import path
from . import views
from .views import RegisterView


urlpatterns = [
    path("", RegisterView.as_view(), name="register"),  # endpoint: /api/core/register/
    path("", views.CoreView.as_view(), name="core"),  # endpoint: /api/core/
]

