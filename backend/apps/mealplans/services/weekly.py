from __future__ import annotations

import re
from decimal import Decimal, ROUND_HALF_UP

from apps.accounts.models import UserProfile
from apps.accounts.services.tdee import calculate_daily_targets

# Base menu designed around this daily calorie target; portions scale linearly.
REFERENCE_CALORIES = 1800
# Healthy fat-loss deficit always applied to weekly meals (TDEE − 500).
FIXED_DEFICIT = 500
_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")

# Low-carb high-protein cycling (protein always 45%).
DAY_MACRO_SPLITS: dict[int, dict[str, Decimal]] = {
    1: {"protein": Decimal("0.45"), "carbs": Decimal("0.35"), "fats": Decimal("0.20")},
    2: {"protein": Decimal("0.45"), "carbs": Decimal("0.35"), "fats": Decimal("0.20")},
    3: {"protein": Decimal("0.45"), "carbs": Decimal("0.25"), "fats": Decimal("0.30")},
    4: {"protein": Decimal("0.45"), "carbs": Decimal("0.25"), "fats": Decimal("0.30")},
    5: {"protein": Decimal("0.45"), "carbs": Decimal("0.15"), "fats": Decimal("0.40")},
    6: {"protein": Decimal("0.45"), "carbs": Decimal("0.15"), "fats": Decimal("0.40")},
    7: {"protein": Decimal("0.45"), "carbs": Decimal("0.15"), "fats": Decimal("0.40")},
}

DAY_NAMES_AR = {
    1: "السبت",
    2: "الأحد",
    3: "الإثنين",
    4: "الثلاثاء",
    5: "الأربعاء",
    6: "الخميس",
    7: "الجمعة",
}

DAY_NAMES_EN = {
    1: "Saturday",
    2: "Sunday",
    3: "Monday",
    4: "Tuesday",
    5: "Wednesday",
    6: "Thursday",
    7: "Friday",
}

MEAL_SLOT_ORDER = ("breakfast", "snack_1", "lunch", "snack_2", "dinner")

MEAL_SLOT_LABELS_AR = {
    "breakfast": "الفطور",
    "snack_1": "وجبة خفيفة 1",
    "lunch": "الغداء",
    "snack_2": "وجبة خفيفة 2",
    "dinner": "العشاء",
}

MEAL_SLOT_LABELS_EN = {
    "breakfast": "Breakfast",
    "snack_1": "Snack 1",
    "lunch": "Lunch",
    "snack_2": "Snack 2",
    "dinner": "Dinner",
}


def scale_factor(target_calories: int) -> Decimal:
    calories = max(1200, int(target_calories or REFERENCE_CALORIES))
    return (Decimal(calories) / Decimal(REFERENCE_CALORIES)).quantize(Decimal("0.01"))


def _distribute_calories(*, base_values: list[int], target: int) -> list[int]:
    """Scale base meal kcal proportionally so the day total equals target exactly."""
    base_total = sum(base_values)
    if base_total <= 0 or not base_values:
        return []
    factor = Decimal(target) / Decimal(base_total)
    raw = [Decimal(v) * factor for v in base_values]
    scaled = [int(r.quantize(Decimal("1"), rounding=ROUND_HALF_UP)) for r in raw]
    diff = target - sum(scaled)
    if diff:
        order = sorted(
            range(len(raw)),
            key=lambda i: raw[i] - Decimal(scaled[i]),
            reverse=(diff > 0),
        )
        step = 1 if diff > 0 else -1
        for i in order[: abs(diff)]:
            scaled[i] += step
    return scaled


def scale_portion_text(text: str, factor: Decimal) -> str:
    """Scale numeric amounts in portion notes (e.g. 100g → 83g at 0.83×)."""
    if not text or factor == 1:
        return text

    def _repl(match: re.Match[str]) -> str:
        raw = match.group(0).replace(",", ".")
        value = Decimal(raw)
        scaled = (value * factor).quantize(
            Decimal("0.1") if "." in raw else Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
        if scaled == scaled.to_integral_value():
            return str(int(scaled))
        return f"{scaled.normalize():f}".rstrip("0").rstrip(".")

    return _NUMBER_RE.sub(_repl, text)


def day_macro_targets(day: int, calories: int) -> dict[str, int]:
    split = DAY_MACRO_SPLITS.get(day, DAY_MACRO_SPLITS[5])
    protein_kcal = Decimal(calories) * split["protein"]
    carbs_kcal = Decimal(calories) * split["carbs"]
    fats_kcal = Decimal(calories) * split["fats"]
    return {
        "calories": calories,
        "protein_g": int((protein_kcal / Decimal("4")).quantize(Decimal("1"))),
        "carbs_g": int((carbs_kcal / Decimal("4")).quantize(Decimal("1"))),
        "fats_g": int((fats_kcal / Decimal("9")).quantize(Decimal("1"))),
        "protein_pct": int(split["protein"] * 100),
        "carbs_pct": int(split["carbs"] * 100),
        "fats_pct": int(split["fats"] * 100),
    }


def build_weekly_plan(*, profile: UserProfile, variety_level: int = 1) -> dict:
    from apps.mealplans.models import WeeklyMealTemplate

    energy = calculate_daily_targets(
        weight_kg=profile.weight_kg,
        height_cm=profile.height_cm,
        age=profile.age,
        gender=profile.gender,
        activity_level=profile.activity_level,
        deficit=FIXED_DEFICIT,
    )
    tdee = int(energy["tdee"])
    deficit = FIXED_DEFICIT
    # Daily meal calories = TDEE − 500 (never below 1200).
    deficit_calories = max(1200, int(energy["goal_calories"]))

    templates = (
        WeeklyMealTemplate.objects.filter(
            is_active=True,
            variety_level__lte=max(1, variety_level),
        )
        .order_by("day_of_week", "sort_order", "meal_slot")
    )

    # Prefer highest variety_level available per day+slot
    best: dict[tuple[int, str], object] = {}
    for row in templates:
        key = (row.day_of_week, row.meal_slot)
        prev = best.get(key)
        if prev is None or row.variety_level > prev.variety_level:
            best[key] = row

    days = []
    scale_factors: list[float] = []
    for day in range(1, 8):
        macros = day_macro_targets(day, deficit_calories)
        day_rows = []
        for slot in MEAL_SLOT_ORDER:
            row = best.get((day, slot))
            if row:
                day_rows.append(row)
        if not day_rows:
            days.append(
                {
                    "day": day,
                    "name_ar": DAY_NAMES_AR[day],
                    "name_en": DAY_NAMES_EN[day],
                    "targets": macros,
                    "meals_calories_total": 0,
                    "scale_factor": 1.0,
                    "meals": [],
                }
            )
            continue

        base_cals = [row.base_calories for row in day_rows]
        day_base_total = sum(base_cals)
        day_factor = (Decimal(deficit_calories) / Decimal(day_base_total)).quantize(
            Decimal("0.01")
        )
        scaled_cals = _distribute_calories(base_values=base_cals, target=deficit_calories)
        scale_factors.append(float(day_factor))

        meals = []
        for row, calories in zip(day_rows, scaled_cals, strict=True):
            slot = row.meal_slot
            quantity_ar = scale_portion_text(row.base_portion_note_ar, day_factor)
            quantity_en = scale_portion_text(row.base_portion_note_en, day_factor)
            meals.append(
                {
                    "slot": slot,
                    "label_ar": MEAL_SLOT_LABELS_AR[slot],
                    "label_en": MEAL_SLOT_LABELS_EN[slot],
                    "title_ar": row.title_ar,
                    "title_en": row.title_en,
                    "description_ar": row.description_ar,
                    "description_en": row.description_en,
                    "portion_note_ar": row.base_portion_note_ar,
                    "portion_note_en": row.base_portion_note_en,
                    "quantity_ar": quantity_ar,
                    "quantity_en": quantity_en,
                    "scale": float(day_factor),
                    "base_calories": row.base_calories,
                    "calories": calories,
                    "protein_g": float((row.base_protein_g * day_factor).quantize(Decimal("0.1"))),
                    "carbs_g": float((row.base_carbs_g * day_factor).quantize(Decimal("0.1"))),
                    "fats_g": float((row.base_fats_g * day_factor).quantize(Decimal("0.1"))),
                }
            )
        days.append(
            {
                "day": day,
                "name_ar": DAY_NAMES_AR[day],
                "name_en": DAY_NAMES_EN[day],
                "targets": macros,
                "meals_calories_total": sum(scaled_cals),
                "scale_factor": float(day_factor),
                "meals": meals,
            }
        )

    avg_scale = (
        round(sum(scale_factors) / len(scale_factors), 2) if scale_factors else 1.0
    )

    return {
        "program": "low_carb_high_protein",
        "program_ar": "قليل الكاربوهيدرات عالي البروتين",
        "program_en": "Low-carb high-protein",
        "weight_kg": float(profile.weight_kg),
        "tdee": tdee,
        "deficit": deficit,
        "fixed_deficit": FIXED_DEFICIT,
        "deficit_calories": deficit_calories,
        "target_calories": deficit_calories,
        "scale_factor": avg_scale,
        "reference_calories": REFERENCE_CALORIES,
        "meals_per_day": 5,
        "note_ar": (
            f"السعرات اليومية = TDEE ({tdee}) − {FIXED_DEFICIT} = {deficit_calories} سعرة. "
            "مجموع وجبات كل يوم يطابق هذا الهدف بالضبط."
        ),
        "note_en": (
            f"Daily calories = TDEE ({tdee}) − {FIXED_DEFICIT} = {deficit_calories} kcal. "
            "Each day's meal total matches this target exactly."
        ),
        "days": days,
    }
