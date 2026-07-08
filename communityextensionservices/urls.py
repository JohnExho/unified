from django.shortcuts import redirect
from django.urls import path
from . import views


app_name = "communityextensionservices"


def root_redirect(request):
    if request.user.is_authenticated:
        return redirect("communityextensionservices:ces-dashboard")
    else:
        return redirect("/communitymembership/login")


urlpatterns = [
    path("", root_redirect, name="ces-root"),
    path("admin/dashboard/", views.dashboard, name="ces-admin-dashboard"),
    path("dashboard/", views.dashboard, name="ces-dashboard"),
    path(
        "dashboard/train-kmeans/",
        views.train_member_kmeans,
        name="ces-train-kmeans",
    ),
    path("members/", views.members, name="ces-members"),
    path("members/new/", views.member_create, name="ces-member-create"),
    path("members/<int:pk>/edit/", views.member_edit, name="ces-member-edit"),
    path("members/<int:pk>/delete/", views.member_delete, name="ces-member-delete"),
    path("dues/", views.dues, name="ces-dues"),
    path("dues/new/", views.dues_create, name="ces-dues-create"),
    path("activities/", views.activities, name="ces-activities"),
    path("activities/new/", views.activity_create, name="ces-activity-create"),
    path("activities/<int:pk>/edit/", views.activity_edit, name="ces-activity-edit"),
    path(
        "activities/<int:pk>/delete/", views.activity_delete, name="ces-activity-delete"
    ),
    path("documents/", views.documents, name="ces-documents"),
    path("documents/new/", views.document_create, name="ces-document-create"),
    path("analytics/", views.analytics, name="ces-analytics"),
    path("reports/", views.reports, name="ces-reports"),
    path("ml-lab/", views.ml_lab, name="ces-ml-lab"),
    path("settings/", views.settings, name="ces-settings"),
]
