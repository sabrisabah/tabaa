from __future__ import annotations

from django.db import models


class MealSlot(models.TextChoices):
    BREAKFAST = "breakfast", "Breakfast"
    SNACK_1 = "snack_1", "Snack 1"
    LUNCH = "lunch", "Lunch"
    SNACK_2 = "snack_2", "Snack 2"
    DINNER = "dinner", "Dinner"


class WeeklyMealTemplate(models.Model):
    """
    Fixed weekly program: same dish names every week.
    Quantities are base portions at REFERENCE_CALORIES and scaled per user.
    """

    day_of_week = models.PositiveSmallIntegerField(
        help_text="1=Saturday … 7=Friday (Iraqi week start).",
    )
    meal_slot = models.CharField(max_length=20, choices=MealSlot.choices)
    title_ar = models.CharField(max_length=200)
    title_en = models.CharField(max_length=200)
    description_ar = models.TextField(blank=True, default="")
    description_en = models.TextField(blank=True, default="")
    # Base macros for one serving at the reference calorie day (1800 kcal)
    base_calories = models.PositiveIntegerField()
    base_protein_g = models.DecimalField(max_digits=6, decimal_places=1)
    base_carbs_g = models.DecimalField(max_digits=6, decimal_places=1)
    base_fats_g = models.DecimalField(max_digits=6, decimal_places=1)
    base_portion_note_ar = models.CharField(max_length=255, blank=True, default="")
    base_portion_note_en = models.CharField(max_length=255, blank=True, default="")
    variety_level = models.PositiveSmallIntegerField(
        default=1,
        help_text="Shown when subscription meal_variety_level >= this value.",
    )
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["day_of_week", "sort_order", "meal_slot"]
        unique_together = [("day_of_week", "meal_slot", "variety_level")]

    def __str__(self) -> str:
        return f"D{self.day_of_week} {self.meal_slot}: {self.title_en}"


# Clinical nutrition plan models (physician editor / patient preview)
from apps.mealplans.clinical_models import (  # noqa: E402
    FoodState,
    MacroEntryMode,
    MacroTemplate,
    NutritionPlan,
    NutritionPlanVersion,
    PlanMealItem,
    PlanStatus,
)

__all__ = [
    "MealSlot",
    "WeeklyMealTemplate",
    "FoodState",
    "MacroEntryMode",
    "MacroTemplate",
    "NutritionPlan",
    "NutritionPlanVersion",
    "PlanMealItem",
    "PlanStatus",
]
