from __future__ import annotations

from decimal import Decimal

from apps.accounts.models import UserProfile

# Activity multipliers applied to BMR to derive TDEE (Total Daily Energy Expenditure).
ACTIVITY_MULTIPLIERS: dict[str, Decimal] = {
    UserProfile.ActivityLevel.SEDENTARY: Decimal("1.2"),
    UserProfile.ActivityLevel.LIGHTLY_ACTIVE: Decimal("1.375"),
    UserProfile.ActivityLevel.MODERATELY_ACTIVE: Decimal("1.55"),
    UserProfile.ActivityLevel.VERY_ACTIVE: Decimal("1.725"),
    UserProfile.ActivityLevel.EXTRA_ACTIVE: Decimal("1.9"),
}

# Mifflin-St Jeor sex constant (kcal/day).
_GENDER_CONSTANTS: dict[str, Decimal] = {
    UserProfile.Gender.MALE: Decimal("5"),
    UserProfile.Gender.FEMALE: Decimal("-161"),
    UserProfile.Gender.OTHER: Decimal("-78"),
}

# Approximate share of TDEE attributed to digestion (TEF).
_TEF_FRACTION = Decimal("0.10")


def calculate_bmr_mifflin_st_jeor(
    *,
    weight_kg: Decimal | float,
    height_cm: Decimal | float,
    age: int,
    gender: str,
) -> Decimal:
    """
    Calculate Basal Metabolic Rate (BMR) using the Mifflin-St Jeor equation.

    Men:   BMR = 10W + 6.25H - 5A + 5
    Women: BMR = 10W + 6.25H - 5A - 161
    """
    weight = Decimal(str(weight_kg))
    height = Decimal(str(height_cm))
    age_decimal = Decimal(str(age))
    gender_constant = _GENDER_CONSTANTS.get(gender, _GENDER_CONSTANTS[UserProfile.Gender.OTHER])

    bmr = (Decimal("10") * weight) + (Decimal("6.25") * height) - (Decimal("5") * age_decimal) + gender_constant
    return bmr.quantize(Decimal("0.01"))


def calculate_tdee_mifflin_st_jeor(
    *,
    weight_kg: Decimal | float,
    height_cm: Decimal | float,
    age: int,
    gender: str,
    activity_level: str,
) -> int:
    """TDEE = BMR × activity multiplier (kcal/day)."""
    bmr = calculate_bmr_mifflin_st_jeor(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
    )
    multiplier = ACTIVITY_MULTIPLIERS.get(
        activity_level,
        ACTIVITY_MULTIPLIERS[UserProfile.ActivityLevel.SEDENTARY],
    )
    tdee = (bmr * multiplier).quantize(Decimal("1"))
    return int(tdee)


def _macros_for_calories(*, weight_kg: Decimal | float, calories: int) -> dict[str, int]:
    protein = max(1, round(float(weight_kg) * 1.8))
    fats = max(1, round(float(weight_kg) * 0.8))
    remaining_kcal = max(0, calories - (protein * 4) - (fats * 9))
    carbs = max(1, remaining_kcal // 4)
    return {
        "target_protein": protein,
        "target_carbs": carbs,
        "target_fats": fats,
    }


def calculate_daily_targets(
    *,
    weight_kg: Decimal | float,
    height_cm: Decimal | float,
    age: int,
    gender: str,
    activity_level: str,
    deficit: int = 0,
) -> dict[str, float | int | dict[str, int]]:
    """
    Return TDEE breakdown (BMR + TEA + TEF) and macro targets.

    Educational decomposition (sums to TDEE):
    - BMR: rest & base needs (Mifflin-St Jeor)
    - TEF: ~10% of TDEE for digestion
    - TEA: remaining calories from movement/activity
    """
    bmr = calculate_bmr_mifflin_st_jeor(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
    )
    tdee = calculate_tdee_mifflin_st_jeor(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity_level,
    )
    bmr_kcal = int(bmr.quantize(Decimal("1")))
    tef = int((Decimal(tdee) * _TEF_FRACTION).quantize(Decimal("1")))
    tea = max(0, tdee - bmr_kcal - tef)

    safe_deficit = max(0, int(deficit))
    goal_calories = max(1200, tdee - safe_deficit)
    macros = _macros_for_calories(weight_kg=weight_kg, calories=goal_calories)

    return {
        "bmr": float(bmr),
        "bmr_kcal": bmr_kcal,
        "tea": tea,
        "tef": tef,
        "tdee": tdee,
        "maintenance_calories": tdee,
        "deficit": safe_deficit,
        "goal_calories": goal_calories,
        "fat_loss_calories": max(1200, tdee - 500),
        "target_calories": goal_calories,
        "target_protein": macros["target_protein"],
        "target_carbs": macros["target_carbs"],
        "target_fats": macros["target_fats"],
        "deficit_options": {
            "0": tdee,
            "250": max(1200, tdee - 250),
            "500": max(1200, tdee - 500),
            "750": max(1200, tdee - 750),
        },
    }
