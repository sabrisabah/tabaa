from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.models import UserProfile
from apps.billing.models import ClinicSettings
from apps.mealplans.clinical_models import (
    MacroEntryMode,
    MacroTemplate,
    NutritionPlan,
    NutritionPlanVersion,
    PlanMealItem,
    PlanStatus,
)
from apps.mealplans.services.macros import energy_decision_support, reconcile_day, resolve_macros

User = get_user_model()


class PlanMealItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlanMealItem
        fields = [
            "id",
            "day_of_week",
            "meal_slot",
            "meal_time",
            "food_name",
            "food_item",
            "quantity",
            "unit",
            "food_state",
            "calories",
            "protein_g",
            "carbs_g",
            "fats_g",
            "alternative_name",
            "alternative_notes",
            "instructions",
            "visible_to_patient",
            "sort_order",
        ]


class NutritionPlanVersionSerializer(serializers.ModelSerializer):
    meal_items = PlanMealItemSerializer(many=True, read_only=True)
    reconciliation = serializers.SerializerMethodField()

    class Meta:
        model = NutritionPlanVersion
        fields = [
            "id",
            "version_number",
            "author",
            "change_summary",
            "is_locked",
            "approved_at",
            "activity_level",
            "bmr_kcal",
            "tdee_kcal",
            "calorie_target",
            "calorie_vs_tdee_diff",
            "calorie_vs_tdee_pct",
            "calorie_target_reason",
            "macro_entry_mode",
            "macro_template",
            "protein_pct",
            "carbs_pct",
            "fats_pct",
            "protein_g",
            "carbs_g",
            "fats_g",
            "protein_g_per_kg",
            "water_instructions",
            "activity_instructions",
            "physician_notes_private",
            "physician_notes_patient",
            "created_at",
            "meal_items",
            "reconciliation",
        ]

    def get_reconciliation(self, obj):
        items = obj.meal_items.all()
        totals = {
            "calories": sum(float(i.calories) for i in items),
            "protein_g": sum(float(i.protein_g) for i in items),
            "carbs_g": sum(float(i.carbs_g) for i in items),
            "fats_g": sum(float(i.fats_g) for i in items),
        }
        return reconcile_day(
            targets={
                "calories": obj.calorie_target,
                "protein_g": obj.protein_g,
                "carbs_g": obj.carbs_g,
                "fats_g": obj.fats_g,
            },
            meal_totals=totals,
        )


class PatientPreviewVersionSerializer(NutritionPlanVersionSerializer):
    """Hide private physician notes from patient view."""

    class Meta(NutritionPlanVersionSerializer.Meta):
        fields = [
            f
            for f in NutritionPlanVersionSerializer.Meta.fields
            if f != "physician_notes_private"
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["meal_items"] = [
            item
            for item in data.get("meal_items", [])
            if item.get("visible_to_patient", True)
        ]
        return data


class NutritionPlanSerializer(serializers.ModelSerializer):
    patient_phone = serializers.CharField(source="patient.username", read_only=True)
    patient_name = serializers.SerializerMethodField()
    latest_version = serializers.SerializerMethodField()

    class Meta:
        model = NutritionPlan
        fields = [
            "id",
            "patient",
            "patient_phone",
            "patient_name",
            "author",
            "name",
            "start_date",
            "duration_days",
            "treatment_objective",
            "status",
            "current_version",
            "is_paediatric_pathway",
            "created_at",
            "updated_at",
            "latest_version",
        ]
        read_only_fields = ["author", "current_version", "created_at", "updated_at"]

    def get_patient_name(self, obj):
        profile = getattr(obj.patient, "profile", None)
        return (profile.full_name if profile else "") or obj.patient.username

    def get_latest_version(self, obj):
        version = obj.versions.order_by("-version_number").first()
        if not version:
            return None
        include_private = self.context.get("include_private", True)
        ser = NutritionPlanVersionSerializer if include_private else PatientPreviewVersionSerializer
        return ser(version, context=self.context).data


class EnergyPreviewSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(required=False)
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    height_cm = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    age = serializers.IntegerField(required=False, min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=UserProfile.Gender.choices, required=False)
    activity_level = serializers.ChoiceField(choices=UserProfile.ActivityLevel.choices)
    calorie_target = serializers.IntegerField(required=False, min_value=500, max_value=10000)


class MacroPreviewSerializer(serializers.Serializer):
    calorie_target = serializers.IntegerField(min_value=500, max_value=10000)
    macro_entry_mode = serializers.ChoiceField(choices=MacroEntryMode.choices)
    macro_template = serializers.ChoiceField(
        choices=MacroTemplate.choices,
        required=False,
        default=MacroTemplate.BALANCED,
    )
    protein_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    carbs_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    fats_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    protein_g = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
    carbs_g = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
    fats_g = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
    remaining_fat_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=40,
    )
    remaining_carb_pct = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        required=False,
        default=60,
    )


class NutritionPlanCreateSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField()
    name = serializers.CharField(max_length=200)
    start_date = serializers.DateField(required=False, allow_null=True)
    duration_days = serializers.IntegerField(required=False, default=7, min_value=1)
    treatment_objective = serializers.CharField(required=False, allow_blank=True, default="")
    activity_level = serializers.ChoiceField(choices=UserProfile.ActivityLevel.choices)
    calorie_target = serializers.IntegerField(min_value=500, max_value=10000)
    calorie_target_reason = serializers.CharField(required=False, allow_blank=True, default="")
    macro_entry_mode = serializers.ChoiceField(
        choices=MacroEntryMode.choices,
        default=MacroEntryMode.PERCENT,
    )
    macro_template = serializers.ChoiceField(
        choices=MacroTemplate.choices,
        required=False,
        default=MacroTemplate.BALANCED,
    )
    protein_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    carbs_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    fats_pct = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    protein_g = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
    carbs_g = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
    fats_g = serializers.DecimalField(max_digits=7, decimal_places=1, required=False)
    protein_g_per_kg = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    water_instructions = serializers.CharField(required=False, allow_blank=True, default="")
    activity_instructions = serializers.CharField(required=False, allow_blank=True, default="")
    physician_notes_private = serializers.CharField(required=False, allow_blank=True, default="")
    physician_notes_patient = serializers.CharField(required=False, allow_blank=True, default="")
    meal_items = serializers.ListField(child=serializers.DictField(), required=False, default=list)

    def validate_patient_id(self, value):
        if not User.objects.filter(pk=value).exists():
            raise ValidationError("Patient not found.")
        return value


def build_version_payload(*, patient_profile: UserProfile, data: dict, author) -> dict:
    settings = ClinicSettings.get_solo()
    energy = energy_decision_support(
        weight_kg=patient_profile.weight_kg,
        height_cm=patient_profile.height_cm,
        age=patient_profile.age,
        gender=patient_profile.gender,
        activity_level=data["activity_level"],
        calorie_target=data["calorie_target"],
        threshold_pct=settings.calorie_target_reason_threshold_pct,
    )
    if energy["requires_calorie_reason"] and not (data.get("calorie_target_reason") or "").strip():
        raise ValidationError(
            {
                "calorie_target_reason": (
                    "Clinical reason required when calorie target differs from TDEE "
                    f"by ≥ {settings.calorie_target_reason_threshold_pct}%."
                ),
            },
        )
    if energy["is_paediatric_pathway"] and not (data.get("calorie_target_reason") or "").strip():
        raise ValidationError(
            {
                "calorie_target_reason": "Paediatric pathway requires clinician rationale for the energy target.",
            },
        )

    protein_g = data.get("protein_g")
    if data.get("protein_g_per_kg") is not None and protein_g is None:
        protein_g = float(patient_profile.weight_kg) * float(data["protein_g_per_kg"])

    macros = resolve_macros(
        calorie_target=data["calorie_target"],
        entry_mode=data.get("macro_entry_mode", MacroEntryMode.PERCENT),
        macro_template=data.get("macro_template", MacroTemplate.BALANCED),
        protein_pct=data.get("protein_pct"),
        carbs_pct=data.get("carbs_pct"),
        fats_pct=data.get("fats_pct"),
        protein_g=protein_g,
        carbs_g=data.get("carbs_g"),
        fats_g=data.get("fats_g"),
    )
    return {**energy, **macros}


@transaction.atomic
def create_nutrition_plan(*, author, data: dict) -> NutritionPlan:
    patient = User.objects.select_related("profile").get(pk=data["patient_id"])
    profile = patient.profile
    payload = build_version_payload(patient_profile=profile, data=data, author=author)
    plan = NutritionPlan.objects.create(
        patient=patient,
        author=author,
        name=data["name"],
        start_date=data.get("start_date"),
        duration_days=data.get("duration_days", 7),
        treatment_objective=data.get("treatment_objective", ""),
        status=PlanStatus.DRAFT,
        current_version=1,
        is_paediatric_pathway=payload["is_paediatric_pathway"],
    )
    version = NutritionPlanVersion.objects.create(
        plan=plan,
        version_number=1,
        author=author,
        change_summary="Initial draft",
        activity_level=data["activity_level"],
        bmr_kcal=payload["bmr_kcal"],
        tdee_kcal=payload["tdee_kcal"],
        calorie_target=payload["calorie_target"],
        calorie_vs_tdee_diff=payload["calorie_vs_tdee_diff"],
        calorie_vs_tdee_pct=payload["calorie_vs_tdee_pct"],
        calorie_target_reason=data.get("calorie_target_reason", ""),
        macro_entry_mode=payload["macro_entry_mode"],
        macro_template=payload["macro_template"],
        protein_pct=payload["protein_pct"],
        carbs_pct=payload["carbs_pct"],
        fats_pct=payload["fats_pct"],
        protein_g=payload["protein_g"],
        carbs_g=payload["carbs_g"],
        fats_g=payload["fats_g"],
        protein_g_per_kg=data.get("protein_g_per_kg"),
        water_instructions=data.get("water_instructions", ""),
        activity_instructions=data.get("activity_instructions", ""),
        physician_notes_private=data.get("physician_notes_private", ""),
        physician_notes_patient=data.get("physician_notes_patient", ""),
    )
    for index, item in enumerate(data.get("meal_items") or []):
        PlanMealItem.objects.create(
            version=version,
            day_of_week=item.get("day_of_week", 1),
            meal_slot=item["meal_slot"],
            meal_time=item.get("meal_time"),
            food_name=item["food_name"],
            food_item_id=item.get("food_item"),
            quantity=item.get("quantity", 1),
            unit=item.get("unit", "g"),
            food_state=item.get("food_state", "edible"),
            calories=item.get("calories", 0),
            protein_g=item.get("protein_g", 0),
            carbs_g=item.get("carbs_g", 0),
            fats_g=item.get("fats_g", 0),
            alternative_name=item.get("alternative_name", ""),
            alternative_notes=item.get("alternative_notes", ""),
            instructions=item.get("instructions", ""),
            visible_to_patient=item.get("visible_to_patient", True),
            sort_order=item.get("sort_order", index),
        )
    return plan


@transaction.atomic
def approve_plan(*, plan: NutritionPlan, actor) -> NutritionPlan:
    version = plan.versions.order_by("-version_number").first()
    if not version:
        raise ValidationError("Plan has no version to approve.")
    if version.is_locked:
        raise ValidationError("Latest version is already approved/locked.")
    recon = NutritionPlanVersionSerializer().get_reconciliation(version)
    if recon["requires_review"]:
        # Allow approve but surface warning via exception only if empty meals and zero targets mismatch huge
        pass
    version.is_locked = True
    version.approved_at = timezone.now()
    version.save(update_fields=["is_locked", "approved_at"])
    plan.status = PlanStatus.ACTIVE
    # Archive other active plans for same patient
    NutritionPlan.objects.filter(patient=plan.patient, status=PlanStatus.ACTIVE).exclude(pk=plan.pk).update(
        status=PlanStatus.ARCHIVED,
    )
    plan.save(update_fields=["status", "updated_at"])
    return plan


@transaction.atomic
def revise_plan(*, plan: NutritionPlan, actor, change_summary: str = "") -> NutritionPlan:
    """Create a new editable version from the latest locked version."""
    latest = plan.versions.order_by("-version_number").first()
    if not latest:
        raise ValidationError("No version to revise.")
    new_number = latest.version_number + 1
    new_version = NutritionPlanVersion.objects.create(
        plan=plan,
        version_number=new_number,
        author=actor,
        change_summary=change_summary or f"Revised from v{latest.version_number}",
        is_locked=False,
        activity_level=latest.activity_level,
        bmr_kcal=latest.bmr_kcal,
        tdee_kcal=latest.tdee_kcal,
        calorie_target=latest.calorie_target,
        calorie_vs_tdee_diff=latest.calorie_vs_tdee_diff,
        calorie_vs_tdee_pct=latest.calorie_vs_tdee_pct,
        calorie_target_reason=latest.calorie_target_reason,
        macro_entry_mode=latest.macro_entry_mode,
        macro_template=latest.macro_template,
        protein_pct=latest.protein_pct,
        carbs_pct=latest.carbs_pct,
        fats_pct=latest.fats_pct,
        protein_g=latest.protein_g,
        carbs_g=latest.carbs_g,
        fats_g=latest.fats_g,
        protein_g_per_kg=latest.protein_g_per_kg,
        water_instructions=latest.water_instructions,
        activity_instructions=latest.activity_instructions,
        physician_notes_private=latest.physician_notes_private,
        physician_notes_patient=latest.physician_notes_patient,
    )
    for item in latest.meal_items.all():
        PlanMealItem.objects.create(
            version=new_version,
            day_of_week=item.day_of_week,
            meal_slot=item.meal_slot,
            meal_time=item.meal_time,
            food_name=item.food_name,
            food_item=item.food_item,
            quantity=item.quantity,
            unit=item.unit,
            food_state=item.food_state,
            calories=item.calories,
            protein_g=item.protein_g,
            carbs_g=item.carbs_g,
            fats_g=item.fats_g,
            alternative_name=item.alternative_name,
            alternative_notes=item.alternative_notes,
            instructions=item.instructions,
            visible_to_patient=item.visible_to_patient,
            sort_order=item.sort_order,
        )
    plan.current_version = new_number
    plan.status = PlanStatus.DRAFT
    plan.save(update_fields=["current_version", "status", "updated_at"])
    return plan
