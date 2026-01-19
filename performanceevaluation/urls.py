from django.urls import path
from . import views

app_name = "performanceevaluation"

urlpatterns = [
    path('dashboard/', views.dashboard, name='performance-evaluation-dashboard'),
]
