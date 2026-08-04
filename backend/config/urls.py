from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView, TemplateView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("clinic.urls")),
    path(
        "",
        TemplateView.as_view(template_name="patient/index.html"),
        name="home",
    ),
    path(
        "patient/",
        TemplateView.as_view(template_name="patient/index.html"),
        name="patient-home",
    ),
    path(
        "patient/app/",
        TemplateView.as_view(template_name="patient/app.html"),
        name="patient-app",
    ),
    path(
        "doctor/",
        TemplateView.as_view(template_name="doctor/index.html"),
        name="doctor-home",
    ),
    path(
        "doctor/app/",
        TemplateView.as_view(template_name="doctor/app.html"),
        name="doctor-app",
    ),
    path(
        "secretary/",
        TemplateView.as_view(template_name="secretary/index.html"),
        name="secretary-home",
    ),
    path(
        "secretary/app/",
        TemplateView.as_view(template_name="secretary/app.html"),
        name="secretary-app",
    ),
]

admin.site.site_header = getattr(settings, "CLINIC_NAME", "Dr. Taiba Nutrition Clinic")
admin.site.site_title = "Dr. Taiba"
admin.site.index_title = "Administration"
