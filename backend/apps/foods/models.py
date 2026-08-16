from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models


class FoodItem(models.Model):
    """
    Master food database entry.

    Nutrition values are stored per serving (serving_size + serving_unit).
    This table is read-only for regular users; only admins may create or edit rows.
    """

    name = models.CharField(max_length=255, db_index=True)
    brand = models.CharField(max_length=255, blank=True, default="")
    barcode = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="UPC/EAN barcode. Nullable for generic whole foods.",
    )

    # Per-serving macronutrients
    calories = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    protein = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Grams of protein per serving.",
    )
    carbs = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Grams of carbohydrates per serving.",
    )
    fats = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Grams of fat per serving.",
    )
    fiber = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
        help_text="Grams of dietary fiber per serving.",
    )

    serving_size = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        help_text="Numeric serving amount (e.g. 100 for 100 g).",
    )
    serving_unit = models.CharField(
        max_length=32,
        help_text="Unit label for the serving (e.g. g, ml, cup, piece).",
    )

    is_active = models.BooleanField(
        default=True,
        help_text="Inactive items are hidden from user search but preserved in logs.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "brand"]
        indexes = [
            models.Index(fields=["name", "brand"]),
        ]
        verbose_name = "Food Item"
        verbose_name_plural = "Food Items"

    def __str__(self) -> str:
        if self.brand:
            return f"{self.name} ({self.brand})"
        return self.name
