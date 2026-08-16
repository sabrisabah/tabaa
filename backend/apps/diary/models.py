from __future__ import annotations

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from apps.foods.models import FoodItem


class DailyDiary(models.Model):
    """
    One diary page per user per calendar day.

    Aggregated nutrition totals are computed in the nutrition service layer,
    not stored redundantly on this model.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="diaries",
    )
    date = models.DateField(db_index=True)
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date"],
                name="unique_user_diary_date",
            ),
        ]
        verbose_name = "Daily Diary"
        verbose_name_plural = "Daily Diaries"

    def __str__(self) -> str:
        return f"{self.user.get_username()} — {self.date.isoformat()}"


class MealLog(models.Model):
    """
    A single food entry within a daily diary, grouped by meal type.

    `quantity` is a multiplier of the FoodItem's serving_size.
    Example: quantity=2.0 on a 100 g serving logs 200 g of that food.
    """

    class MealType(models.TextChoices):
        BREAKFAST = "breakfast", "Breakfast"
        LUNCH = "lunch", "Lunch"
        DINNER = "dinner", "Dinner"
        SNACK = "snack", "Snack"

    daily_diary = models.ForeignKey(
        DailyDiary,
        on_delete=models.CASCADE,
        related_name="meal_logs",
    )
    meal_type = models.CharField(max_length=20, choices=MealType.choices)
    food_item = models.ForeignKey(
        FoodItem,
        on_delete=models.PROTECT,
        related_name="meal_logs",
        help_text="Reference to master food data; PROTECT prevents orphaning logs.",
    )
    quantity = models.FloatField(
        validators=[MinValueValidator(0.01)],
        help_text="Number of servings consumed (multiplier of FoodItem.serving_size).",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["meal_type", "created_at"]
        indexes = [
            models.Index(fields=["daily_diary", "meal_type"]),
        ]
        verbose_name = "Meal Log"
        verbose_name_plural = "Meal Logs"

    def __str__(self) -> str:
        return (
            f"{self.get_meal_type_display()}: "
            f"{self.food_item.name} x{self.quantity}"
        )
