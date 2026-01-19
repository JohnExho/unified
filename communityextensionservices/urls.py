from django.urls import path
from . import views

app_name = "communityextensionservices"

urlpatterns = [
    path('dashboard/', views.dashboard, name='ces-dashboard'),
]
