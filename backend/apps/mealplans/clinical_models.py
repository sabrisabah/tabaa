from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models


class MealSlot(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    SNACK_1 = "snack_1", "Snack 1"
    LUNCH = "lunch", "Lunch"
    SNACK_2 = "snack_2", "Snack 2"
    DINNER = "dinner", "Dinner"


class PlanStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class MacroEntryMode(models.TextChoices):
    PERCENT = "percent", "Percentage"
    PROTEIN_FIRST = "protein_first", "Protein-first grams"
    CUSTOM_GRAMS = "custom_grams", "Custom grams"


class MacroTemplate(models.TextChoices):
    BALANCED = "balanced", "Balanced 25/45/30"
    HIGHER_PROTEIN = "higher_protein", "Higher protein 30/40/30"
    MODERATE_CARB = "moderate_carb", "Moderate carbohydrate 30/35/35"
    CUSTOM = "custom", "Custom"


MACRO_TEMPLATE_PERCENTS = {
    MacroTemplate.BALANCED: (25, 45, 30),
    MacroTemplate.HIGHER_PROTEIN: (30, 40, 30),
    MacroTemplate.MODERATE_CARB: (30, 35, 35),
}


class FoodState(models.TextChoices):
    RAW = "raw", "Raw"
    COOKED = "cooked", "Cooked"
    DRAINED = "drained", "Drained"
    EDIBLE = "edible", "Edible portion"


class NutritionPlan(models.Model):
    """Physician-authored clinical nutrition plan for a patient (د. طيبة)."""

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="nutrition_plans",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="authored_nutrition_plans",
    )
    name = models.CharField(max_length=200)
    start_date = models.DateField(null=True, blank=True)
    duration_days = models.PositiveSmallIntegerField(default=7)
    treatment_objective = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=PlanStatus.choices, default=PlanStatus.DRAFT)
    current_version = models.PositiveIntegerField(default=1)
    is_paediatric_pathway = models.BooleanField(
        default=False,
        help_text="True when patient age < 18 — adult deficit rules must not auto-apply.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.name} · {self.patient_id} v{self.current_version}"


class NutritionPlanVersion(models.Model):
    """Immutable snapshot once approved; drafts remain editable."""

    plan = models.ForeignKey(NutritionPlan, on_delete=models.CASCADE, related_name="versions")
    version_number = models.PositiveIntegerField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    change_summary = models.TextField(blank=True, default="")
    is_locked = models.BooleanField(default=False)
    approved_at = models.DateTimeField(null=True, blank=True)

    # Energy
    activity_level = models.CharField(max_length=20, blank=True, default="")
    bmr_kcal = models.PositiveIntegerField(default=0)
    tdee_kcal = models.PositiveIntegerField(default=0)
    calorie_target = models.PositiveIntegerField(default=0)
    calorie_vs_tdee_diff = models.IntegerField(default=0)
    calorie_vs_tdee_pct = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    calorie_target_reason = models.TextField(blank=True, default="")

    # Macros
    macro_entry_mode = models.CharField(
        max_length=20,
        choices=MacroEntryMode.choices,
        default=MacroEntryMode.PERCENT,
    )
    macro_template = models.CharField(
        max_length=32,
        choices=MacroTemplate.choices,
        default=MacroTemplate.BALANCED,
    )
    protein_pct = models.DecimalField(max_digits=5, decimal_places=2, default=25)
    carbs_pct = models.DecimalField(max_digits=5, decimal_places=2, default=45)
    fats_pct = models.DecimalField(max_digits=5, decimal_places=2, default=30)
    protein_g = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    carbs_g = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    fats_g = models.DecimalField(max_digits=7, decimal_places=1, default=0)
    protein_g_per_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    water_instructions = models.TextField(blank=True, default="")
    activity_instructions = models.TextField(blank=True, default="")
    physician_notes_private = models.TextField(blank=True, default="")
    physician_notes_patient = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version_number"]
        unique_together = [("plan", "version_number")]

    def __str__(self) -> str:
        return f"Plan {self.plan_id} v{self.version_number}"


class PlanMealItem(models.Model):
    version = models.ForeignKey(
        NutritionPlanVersion,
        on_delete=models.CASCADE,
        related_name="meal_items",
    )
    day_of_week = models.PositiveSmallIntegerField(
        default=1,
        help_text="1=Saturday … 7=Friday, or 0 for single-day plans.",
    )
    meal_slot = models.CharField(max_length=20, choices=MealSlot.choices)
    meal_time = models.TimeField(null=True, blank=True)
    food_name = models.CharField(max_length=200)
    food_item = models.ForeignKey(
        "foods.FoodItem",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="plan_meal_items",
    )
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit = models.CharField(max_length=40, default="g")
    food_state = models.CharField(
        max_length=20,
        choices=FoodState.choices,
        default=FoodState.EDIBLE,
    )
    calories = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    protein_g = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    carbs_g = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    fats_g = models.DecimalField(max_digits=8, decimal_places=1, default=0)
    alternative_name = models.CharField(max_length=200, blank=True, default="")
    alternative_notes = models.CharField(max_length=255, blank=True, default="")
    instructions = models.TextField(blank=True, default="")
    visible_to_patient = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["day_of_week", "sort_order", "meal_slot", "id"]
