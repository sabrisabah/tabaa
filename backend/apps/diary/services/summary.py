from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce

from apps.diary.models import MealLog


def get_consumed_totals_for_date(
    user: AbstractBaseUser,
    target_date: datetime.date,
) -> dict[str, Decimal]:
    """
    Sum consumed macros for a user on a given date using database-level math.

    Each MealLog contributes: quantity × FoodItem.<nutrient> (per serving).
    """
    totals = (
        MealLog.objects.filter(
            daily_diary__user=user,
            daily_diary__date=target_date,
        )
        .aggregate(
            total_calories=Coalesce(
                Sum(
                    F("quantity") * F("food_item__calories"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
            total_protein=Coalesce(
                Sum(
                    F("quantity") * F("food_item__protein"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
            total_carbs=Coalesce(
                Sum(
                    F("quantity") * F("food_item__carbs"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
            total_fats=Coalesce(
                Sum(
                    F("quantity") * F("food_item__fats"),
                    output_field=DecimalField(max_digits=14, decimal_places=2),
                ),
                Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=2)),
            ),
        )
    )

    return {
        "calories": totals["total_calories"],
        "protein": totals["total_protein"],
        "carbs": totals["total_carbs"],
        "fats": totals["total_fats"],
    }


def build_today_summary_payload(user: AbstractBaseUser, target_date: datetime.date) -> dict[str, Any]:
    """Combine consumed totals with profile targets for the summary API response."""
    from apps.accounts.models import UserProfile

    consumed = get_consumed_totals_for_date(user, target_date)

    try:
        profile = user.profile  # type: ignore[attr-defined]
    except UserProfile.DoesNotExist as exc:
        raise UserProfile.DoesNotExist(
            "User profile is required to return target values."
        ) from exc

    return {
        "date": target_date.isoformat(),
        "consumed": {
            "calories": float(consumed["calories"]),
            "protein": float(consumed["protein"]),
            "carbs": float(consumed["carbs"]),
            "fats": float(consumed["fats"]),
        },
        "targets": {
            "calories": profile.target_calories,
            "protein": profile.target_protein,
            "carbs": profile.target_carbs,
            "fats": profile.target_fats,
        },
        "remaining": {
            "calories": profile.target_calories - float(consumed["calories"]),
            "protein": profile.target_protein - float(consumed["protein"]),
            "carbs": profile.target_carbs - float(consumed["carbs"]),
            "fats": profile.target_fats - float(consumed["fats"]),
        },
    }
