from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.http import FileResponse, HttpResponseNotFound
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.serializers import PhoneTokenObtainPairSerializer

admin.site.site_header = "د. طيبة"
admin.site.site_title = "د. طيبة"
admin.site.index_title = "لوحة التحكم"


class PhoneTokenObtainPairView(TokenObtainPairView):
    serializer_class = PhoneTokenObtainPairSerializer


def spa_index(_request, unused=""):
    index = Path(settings.BASE_DIR).parent / "frontend" / "dist" / "index.html"
    if not index.exists():
        return HttpResponseNotFound("Frontend build is missing.")
    return FileResponse(index.open("rb"), content_type="text/html")


urlpatterns = [
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

frontend_index = Path(settings.BASE_DIR).parent / "frontend" / "dist" / "index.html"
if frontend_index.exists():
    urlpatterns += [
        re_path(r"^(?!api/|admin/|static/).*$", spa_index),
    ]
else:
    urlpatterns.insert(
        0,
        path(
            "",
            RedirectView.as_view(url="/admin/login/?next=/admin/", permanent=False),
            name="root-admin-login",
        ),
    )
