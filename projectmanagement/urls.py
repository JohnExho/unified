from django.urls import path
from .views import (
    dashboard,
    settings,
)

app_name = "projectmanagement"

urlpatterns = [
    path('dashboard/', dashboard, name='pm-dashboard'),
    path('settings/', settings, name='pm-settings'),
]
