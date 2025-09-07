from django.urls import path
from . import views


urlpatterns = [
    path("", views.CoreView.as_view(), name="core"),  # endpoint: /api/core/
]

