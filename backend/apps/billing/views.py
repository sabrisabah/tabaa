from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.accounts.permissions import IsClinicStaff, IsDoctor, IsSecretaryOrDoctor
from apps.accounts.serializers import UserProfileSerializer
from apps.billing.models import ClinicService, ClinicSettings, Invoice
from apps.billing.serializers import (
    ClinicServiceSerializer,
    ClinicSettingsSerializer,
    DiscountSerializer,
    InvoiceCreateSerializer,
    InvoiceSerializer,
    PaymentSerializer,
)
from apps.billing.services import (
    apply_discount,
    cancel_or_refund_invoice,
    create_invoice,
    record_payment,
    revenue_summary,
)

User = get_user_model()


class ClinicSettingsView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def get(self, request: Request) -> Response:
        return Response(ClinicSettingsSerializer(ClinicSettings.get_solo()).data)

    def patch(self, request: Request) -> Response:
        if not IsDoctor().has_permission(request, self):
            return Response({"detail": "تعديل الإعدادات للطبيبة فقط."}, status=403)
        settings_obj = ClinicSettings.get_solo()
        serializer = ClinicSettingsSerializer(settings_obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ClinicServiceListCreateView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def get(self, request: Request) -> Response:
        active_only = request.query_params.get("active", "1") != "0"
        qs = ClinicService.objects.prefetch_related("variants").all()
        if active_only:
            qs = qs.filter(is_active=True)
        return Response(ClinicServiceSerializer(qs, many=True).data)

    def post(self, request: Request) -> Response:
        if not IsDoctor().has_permission(request, self):
            return Response({"detail": "إضافة الخدمات للطبيبة فقط."}, status=403)
        serializer = ClinicServiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service = serializer.save()
        return Response(ClinicServiceSerializer(service).data, status=status.HTTP_201_CREATED)


class ClinicServiceDetailView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request: Request, pk: int) -> Response:
        try:
            service = ClinicService.objects.get(pk=pk)
        except ClinicService.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        serializer = ClinicServiceSerializer(service, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ClinicServiceSerializer(service).data)


class PatientSearchView(APIView):
    """Staff patient lookup for invoicing / nutrition plans."""

    permission_classes = [IsClinicStaff]

    def get(self, request: Request) -> Response:
        q = (request.query_params.get("q") or "").strip()
        qs = UserProfile.objects.filter(clinic_role=UserProfile.ClinicRole.PATIENT).select_related("user")
        if q:
            qs = qs.filter(
                Q(full_name__icontains=q)
                | Q(user__username__icontains=q)
                | Q(patient_file_number__icontains=q),
            )
        qs = qs.distinct().order_by("full_name", "user__username")[:40]
        return Response(UserProfileSerializer(qs, many=True).data)


def _get_patient_profile(user_id: int) -> UserProfile | None:
    try:
        return UserProfile.objects.select_related("user").get(
            user_id=user_id,
            clinic_role=UserProfile.ClinicRole.PATIENT,
        )
    except UserProfile.DoesNotExist:
        return None


class PatientTdeeVisibilityView(APIView):
    """Doctor toggles TDEE calculator visibility for a specific patient."""

    permission_classes = [IsDoctor]

    def patch(self, request: Request, user_id: int) -> Response:
        profile = _get_patient_profile(user_id)
        if profile is None:
            return Response({"detail": "Patient not found."}, status=404)

        if "show_tdee_calculator" not in request.data:
            return Response({"detail": "show_tdee_calculator is required."}, status=400)

        profile.show_tdee_calculator = bool(request.data.get("show_tdee_calculator"))
        profile.save(update_fields=["show_tdee_calculator", "updated_at"])
        return Response(UserProfileSerializer(profile).data)


class PatientEnergyTargetsView(APIView):
    """Doctor calculates and saves energy/macro targets onto a patient profile."""

    permission_classes = [IsDoctor]

    def patch(self, request: Request, user_id: int) -> Response:
        profile = _get_patient_profile(user_id)
        if profile is None:
            return Response({"detail": "Patient not found."}, status=404)

        allowed = {
            "age",
            "gender",
            "weight_kg",
            "height_cm",
            "activity_level",
            "target_calories",
            "target_protein",
            "target_carbs",
            "target_fats",
            "show_tdee_calculator",
        }
        update_fields = ["updated_at"]
        for field in allowed:
            if field not in request.data:
                continue
            setattr(profile, field, request.data.get(field))
            update_fields.append(field)

        if len(update_fields) == 1:
            return Response({"detail": "No energy fields provided."}, status=400)

        profile.save(update_fields=update_fields)
        return Response(UserProfileSerializer(profile).data)


class InvoiceListCreateView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def get(self, request: Request) -> Response:
        qs = Invoice.objects.select_related("patient", "created_by").prefetch_related("items")
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(payment_status=status_filter)
        patient_id = request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return Response(InvoiceSerializer(qs[:100], many=True).data)

    def post(self, request: Request) -> Response:
        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        patient = User.objects.get(pk=data["patient_id"])
        approved_by = None
        if data.get("discount_approved_by_id"):
            approved_by = User.objects.filter(pk=data["discount_approved_by_id"]).first()
        invoice = create_invoice(
            patient=patient,
            created_by=request.user,
            items=data["items"],
            notes=data.get("notes", ""),
            discount_percent=data.get("discount_percent"),
            discount_reason=data.get("discount_reason", ""),
            discount_reason_custom=data.get("discount_reason_custom", ""),
            discount_approved_by=approved_by,
            show_discount_reason_on_receipt=data.get("show_discount_reason_on_receipt", False),
        )
        invoice = Invoice.objects.prefetch_related("items", "audit_logs").get(pk=invoice.pk)
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)


class InvoiceDetailView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def get(self, request: Request, pk: int) -> Response:
        try:
            invoice = Invoice.objects.prefetch_related("items", "audit_logs").get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        return Response(InvoiceSerializer(invoice).data)


class InvoicePayView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def post(self, request: Request, pk: int) -> Response:
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invoice = record_payment(
            invoice=invoice,
            amount_paid_iqd=serializer.validated_data["amount_paid_iqd"],
            payment_method=serializer.validated_data["payment_method"],
            actor=request.user,
        )
        return Response(InvoiceSerializer(invoice).data)


class InvoiceDiscountView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def post(self, request: Request, pk: int) -> Response:
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        serializer = DiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        approved_by = None
        if data.get("discount_approved_by_id"):
            approved_by = User.objects.filter(pk=data["discount_approved_by_id"]).first()
        invoice = apply_discount(
            invoice=invoice,
            percent=data["discount_percent"],
            reason=data["discount_reason"],
            reason_custom=data.get("discount_reason_custom", ""),
            entered_by=request.user,
            approved_by=approved_by,
        )
        return Response(InvoiceSerializer(invoice).data)


class InvoiceCancelRefundView(APIView):
    permission_classes = [IsDoctor]

    def post(self, request: Request, pk: int) -> Response:
        try:
            invoice = Invoice.objects.get(pk=pk)
        except Invoice.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        action = request.data.get("action")
        reason = request.data.get("reason", "")
        invoice = cancel_or_refund_invoice(
            invoice=invoice,
            actor=request.user,
            action=action,
            reason=reason,
        )
        return Response(InvoiceSerializer(invoice).data)


class RevenueReportView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def get(self, request: Request) -> Response:
        # Secretaries see operational scope; doctors see all (same for now).
        return Response(
            revenue_summary(
                date_from=request.query_params.get("date_from"),
                date_to=request.query_params.get("date_to"),
            ),
        )
