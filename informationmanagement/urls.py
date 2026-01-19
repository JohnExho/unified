from django.urls import path
from . import views

app_name = "informationmanagement"

urlpatterns = [
    path('dashboard/', views.dashboard, name='information-dashboard'),
]
