from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import PhoneTokenObtainPairSerializer

admin.site.site_header = "د. طيبة"
admin.site.site_title = "د. طيبة"
admin.site.index_title = "لوحة التحكم"

class PhoneTokenObtainPairView(TokenObtainPairView):
    serializer_class = PhoneTokenObtainPairSerializer


urlpatterns = [
    path(
        "",
        RedirectView.as_view(url="/admin/login/?next=/admin/", permanent=False),
        name="root-admin-login",
    ),
    path("admin/", admin.site.urls),
    path(
        "api/auth/token/",
        PhoneTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.diary.urls")),
    path("api/", include("apps.foods.urls")),
    path("api/", include("apps.subscriptions.urls")),
    path("api/", include("apps.mealplans.urls")),
    path("api/", include("apps.billing.urls")),
]
