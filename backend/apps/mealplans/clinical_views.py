from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.accounts.permissions import IsDoctor, IsSecretaryOrDoctor
from apps.billing.models import ClinicSettings
from apps.mealplans.clinical_models import NutritionPlan, PlanStatus
from apps.mealplans.clinical_serializers import (
    EnergyPreviewSerializer,
    MacroPreviewSerializer,
    NutritionPlanCreateSerializer,
    NutritionPlanSerializer,
    PatientPreviewVersionSerializer,
    approve_plan,
    create_nutrition_plan,
    revise_plan,
)
from apps.mealplans.services.macros import energy_decision_support, resolve_macros

User = get_user_model()


class EnergyPreviewView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def post(self, request: Request) -> Response:
        serializer = EnergyPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data.get("patient_id"):
            try:
                profile = User.objects.select_related("profile").get(pk=data["patient_id"]).profile
            except (User.DoesNotExist, UserProfile.DoesNotExist):
                return Response({"detail": "Patient not found."}, status=404)
            weight_kg = profile.weight_kg
            height_cm = profile.height_cm
            age = profile.age
            gender = profile.gender
        else:
            for key in ("weight_kg", "height_cm", "age", "gender"):
                if key not in data:
                    return Response({"detail": f"{key} required when patient_id omitted."}, status=400)
            weight_kg = data["weight_kg"]
            height_cm = data["height_cm"]
            age = data["age"]
            gender = data["gender"]

        threshold = ClinicSettings.get_solo().calorie_target_reason_threshold_pct
        result = energy_decision_support(
            weight_kg=weight_kg,
            height_cm=height_cm,
            age=age,
            gender=gender,
            activity_level=data["activity_level"],
            calorie_target=data.get("calorie_target"),
            threshold_pct=threshold,
        )
        return Response(result)


class MacroPreviewView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def post(self, request: Request) -> Response:
        serializer = MacroPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = resolve_macros(
            calorie_target=data["calorie_target"],
            entry_mode=data["macro_entry_mode"],
            macro_template=data.get("macro_template"),
            protein_pct=data.get("protein_pct"),
            carbs_pct=data.get("carbs_pct"),
            fats_pct=data.get("fats_pct"),
            protein_g=data.get("protein_g"),
            carbs_g=data.get("carbs_g"),
            fats_g=data.get("fats_g"),
            remaining_fat_pct=data.get("remaining_fat_pct", 40),
            remaining_carb_pct=data.get("remaining_carb_pct", 60),
        )
        return Response({k: float(v) if hasattr(v, "as_tuple") else v for k, v in result.items()})


class NutritionPlanListCreateView(APIView):
    permission_classes = [IsDoctor]

    def get(self, request: Request) -> Response:
        qs = NutritionPlan.objects.select_related("patient", "author").prefetch_related("versions__meal_items")
        patient_id = request.query_params.get("patient_id")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(NutritionPlanSerializer(qs[:50], many=True).data)

    def post(self, request: Request) -> Response:
        serializer = NutritionPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = create_nutrition_plan(author=request.user, data=serializer.validated_data)
        plan = NutritionPlan.objects.prefetch_related("versions__meal_items").get(pk=plan.pk)
        return Response(NutritionPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


class NutritionPlanDetailView(APIView):
    permission_classes = [IsSecretaryOrDoctor]

    def get(self, request: Request, pk: int) -> Response:
        try:
            plan = NutritionPlan.objects.prefetch_related("versions__meal_items").get(pk=pk)
        except NutritionPlan.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        return Response(NutritionPlanSerializer(plan).data)


class NutritionPlanApproveView(APIView):
    permission_classes = [IsDoctor]

    def post(self, request: Request, pk: int) -> Response:
        try:
            plan = NutritionPlan.objects.prefetch_related("versions__meal_items").get(pk=pk)
        except NutritionPlan.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        plan = approve_plan(plan=plan, actor=request.user)
        plan = NutritionPlan.objects.prefetch_related("versions__meal_items").get(pk=plan.pk)
        return Response(NutritionPlanSerializer(plan).data)


class NutritionPlanReviseView(APIView):
    permission_classes = [IsDoctor]

    def post(self, request: Request, pk: int) -> Response:
        try:
            plan = NutritionPlan.objects.prefetch_related("versions__meal_items").get(pk=pk)
        except NutritionPlan.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        plan = revise_plan(
            plan=plan,
            actor=request.user,
            change_summary=request.data.get("change_summary", ""),
        )
        plan = NutritionPlan.objects.prefetch_related("versions__meal_items").get(pk=plan.pk)
        return Response(NutritionPlanSerializer(plan).data)


class NutritionPlanArchiveView(APIView):
    permission_classes = [IsDoctor]

    def post(self, request: Request, pk: int) -> Response:
        try:
            plan = NutritionPlan.objects.get(pk=pk)
        except NutritionPlan.DoesNotExist:
            return Response({"detail": "Not found."}, status=404)
        plan.status = PlanStatus.ARCHIVED
        plan.save(update_fields=["status", "updated_at"])
        return Response(NutritionPlanSerializer(plan).data)


class MyNutritionPlanView(APIView):
    """Patient-facing read-only approved plan preview."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        plan = (
            NutritionPlan.objects.filter(patient=request.user, status=PlanStatus.ACTIVE)
            .prefetch_related("versions__meal_items")
            .order_by("-updated_at")
            .first()
        )
        if not plan:
            return Response({"detail": "No active nutrition plan."}, status=404)
        data = NutritionPlanSerializer(plan, context={"include_private": False}).data
        latest = plan.versions.filter(is_locked=True).order_by("-version_number").first()
        if latest:
            data["latest_version"] = PatientPreviewVersionSerializer(latest).data
        return Response(data)
