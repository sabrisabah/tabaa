from django.urls import path

from apps.billing.views import (
    ClinicServiceDetailView,
    ClinicServiceListCreateView,
    ClinicSettingsView,
    InvoiceCancelRefundView,
    InvoiceDetailView,
    InvoiceDiscountView,
    InvoiceListCreateView,
    InvoicePayView,
    PatientEnergyTargetsView,
    PatientSearchView,
    PatientTdeeVisibilityView,
    RevenueReportView,
)

urlpatterns = [
    path("clinic/settings/", ClinicSettingsView.as_view(), name="clinic-settings"),
    path("clinic/services/", ClinicServiceListCreateView.as_view(), name="clinic-services"),
    path("clinic/services/<int:pk>/", ClinicServiceDetailView.as_view(), name="clinic-service-detail"),
    path("clinic/patients/", PatientSearchView.as_view(), name="clinic-patients"),
    path(
        "clinic/patients/<int:user_id>/tdee-visibility/",
        PatientTdeeVisibilityView.as_view(),
        name="clinic-patient-tdee-visibility",
    ),
    path(
        "clinic/patients/<int:user_id>/energy-targets/",
        PatientEnergyTargetsView.as_view(),
        name="clinic-patient-energy-targets",
    ),
    path("clinic/invoices/", InvoiceListCreateView.as_view(), name="clinic-invoices"),
    path("clinic/invoices/<int:pk>/", InvoiceDetailView.as_view(), name="clinic-invoice-detail"),
    path("clinic/invoices/<int:pk>/pay/", InvoicePayView.as_view(), name="clinic-invoice-pay"),
    path("clinic/invoices/<int:pk>/discount/", InvoiceDiscountView.as_view(), name="clinic-invoice-discount"),
    path(
        "clinic/invoices/<int:pk>/cancel-refund/",
        InvoiceCancelRefundView.as_view(),
        name="clinic-invoice-cancel-refund",
    ),
    path("clinic/reports/revenue/", RevenueReportView.as_view(), name="clinic-revenue-report"),
]
