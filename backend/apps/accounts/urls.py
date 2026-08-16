from django.urls import path

from apps.accounts.views import MyProfileView, RegisterView, TdeePreviewView, WeightLogView

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("profile/tdee-preview/", TdeePreviewView.as_view(), name="tdee-preview"),
    path("profile/me/", MyProfileView.as_view(), name="profile-me"),
    path("profile/weight-logs/", WeightLogView.as_view(), name="weight-logs"),
]
