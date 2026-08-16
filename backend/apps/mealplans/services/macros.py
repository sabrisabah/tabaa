from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from rest_framework.exceptions import ValidationError

from apps.accounts.services.tdee import (
    ACTIVITY_MULTIPLIERS,
    calculate_bmr_mifflin_st_jeor,
    calculate_tdee_mifflin_st_jeor,
)
from apps.mealplans.clinical_models import MACRO_TEMPLATE_PERCENTS, MacroEntryMode, MacroTemplate

Q1 = Decimal("0.1")
Q2 = Decimal("0.01")


def _d(value) -> Decimal:
    return Decimal(str(value))


def macros_from_percent(*, calories: int | Decimal, protein_pct, carbs_pct, fats_pct) -> dict:
    """Percentage-to-gram conversion per clinic nutrition spec."""
    p = _d(protein_pct)
    c = _d(carbs_pct)
    f = _d(fats_pct)
    total = p + c + f
    if total != Decimal("100"):
        raise ValidationError(
            {"macros": f"Protein % + Carbohydrate % + Fat % must equal 100% (got {total})."},
        )
    cal = _d(calories)
    protein_g = ((cal * p / Decimal("100")) / Decimal("4")).quantize(Q1, rounding=ROUND_HALF_UP)
    carbs_g = ((cal * c / Decimal("100")) / Decimal("4")).quantize(Q1, rounding=ROUND_HALF_UP)
    fats_g = ((cal * f / Decimal("100")) / Decimal("9")).quantize(Q1, rounding=ROUND_HALF_UP)
    return {
        "protein_pct": p.quantize(Q2),
        "carbs_pct": c.quantize(Q2),
        "fats_pct": f.quantize(Q2),
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fats_g": fats_g,
    }


def macros_protein_first(
    *,
    calories: int | Decimal,
    protein_g: Decimal | float | int,
    remaining_fat_pct: Decimal | float = 40,
    remaining_carb_pct: Decimal | float = 60,
) -> dict:
    """
    Protein-first gram method:
    protein calories first, then allocate remaining calories to fat/carb by physician rules.
    """
    cal = _d(calories)
    protein = _d(protein_g)
    protein_kcal = protein * Decimal("4")
    remaining = cal - protein_kcal
    if remaining < 0:
        raise ValidationError(
            {"protein_g": "Protein calories exceed total prescribed calories (negative remaining)."},
        )
    fat_share = _d(remaining_fat_pct)
    carb_share = _d(remaining_carb_pct)
    if fat_share + carb_share != Decimal("100"):
        raise ValidationError(
            {"remaining_split": "Remaining fat% + carb% must equal 100%."},
        )
    fats_g = ((remaining * fat_share / Decimal("100")) / Decimal("9")).quantize(Q1, rounding=ROUND_HALF_UP)
    carbs_g = ((remaining * carb_share / Decimal("100")) / Decimal("4")).quantize(Q1, rounding=ROUND_HALF_UP)
    protein_pct = ((protein_kcal / cal) * Decimal("100")).quantize(Q2, rounding=ROUND_HALF_UP) if cal else Decimal("0")
    carbs_pct = (((carbs_g * Decimal("4")) / cal) * Decimal("100")).quantize(Q2, rounding=ROUND_HALF_UP) if cal else Decimal("0")
    fats_pct = (((fats_g * Decimal("9")) / cal) * Decimal("100")).quantize(Q2, rounding=ROUND_HALF_UP) if cal else Decimal("0")
    return {
        "protein_g": protein.quantize(Q1),
        "carbs_g": carbs_g,
        "fats_g": fats_g,
        "protein_pct": protein_pct,
        "carbs_pct": carbs_pct,
        "fats_pct": fats_pct,
        "remaining_calories": remaining.quantize(Decimal("1")),
    }


def apply_macro_template(template: str) -> tuple[Decimal, Decimal, Decimal]:
    if template == MacroTemplate.CUSTOM:
        raise ValidationError({"macro_template": "Custom template requires explicit percentages."})
    if template not in MACRO_TEMPLATE_PERCENTS:
        raise ValidationError({"macro_template": "Unknown macro template."})
    p, c, f = MACRO_TEMPLATE_PERCENTS[template]
    return Decimal(p), Decimal(c), Decimal(f)


def energy_decision_support(
    *,
    weight_kg,
    height_cm,
    age: int,
    gender: str,
    activity_level: str,
    calorie_target: int | None = None,
    threshold_pct: int = 15,
) -> dict:
    """
    Adult Mifflin-St Jeor decision support. Physician keeps final calorie control.
    Under-18 callers should set paediatric pathway and skip auto deficit.
    """
    is_paediatric = age < 18
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
    prescribed = int(calorie_target) if calorie_target is not None else tdee
    diff = prescribed - tdee
    pct = (Decimal(diff) / Decimal(tdee) * Decimal("100")).quantize(Q2) if tdee else Decimal("0")
    requires_reason = abs(pct) >= Decimal(threshold_pct)
    return {
        "is_paediatric_pathway": is_paediatric,
        "bmr_kcal": int(bmr.quantize(Decimal("1"))),
        "tdee_kcal": tdee,
        "activity_level": activity_level,
        "activity_factor": float(ACTIVITY_MULTIPLIERS.get(activity_level, Decimal("1.2"))),
        "calorie_target": prescribed,
        "calorie_vs_tdee_diff": diff,
        "calorie_vs_tdee_pct": pct,
        "requires_calorie_reason": requires_reason,
        "safeguard_note": (
            "Patients under 18 require paediatric pathway; adult deficit rules must not auto-apply."
            if is_paediatric
            else ""
        ),
    }


def reconcile_day(*, targets: dict, meal_totals: dict, tolerance: dict | None = None) -> dict:
    """End-of-day reconciliation with configurable tolerance flags."""
    tol = tolerance or {"calories": 50, "protein_g": 5, "carbs_g": 10, "fats_g": 5}
    keys = [
        ("calories", "calories", "Energy"),
        ("protein_g", "protein_g", "Protein"),
        ("carbs_g", "carbs_g", "Carbohydrate"),
        ("fats_g", "fats_g", "Fat"),
    ]
    rows = []
    out_of_tolerance = False
    for target_key, meal_key, label in keys:
        target = _d(targets.get(target_key, 0))
        actual = _d(meal_totals.get(meal_key, 0))
        diff = actual - target
        limit = _d(tol.get(meal_key if meal_key != "calories" else "calories", 0))
        flagged = abs(diff) > limit
        if flagged:
            out_of_tolerance = True
        rows.append(
            {
                "indicator": label,
                "target": float(target),
                "meal_plan_total": float(actual),
                "difference": float(diff),
                "flagged": flagged,
            },
        )
    return {"rows": rows, "out_of_tolerance": out_of_tolerance, "requires_review": out_of_tolerance}


def resolve_macros(
    *,
    calorie_target: int,
    entry_mode: str,
    macro_template: str = MacroTemplate.BALANCED,
    protein_pct=None,
    carbs_pct=None,
    fats_pct=None,
    protein_g=None,
    carbs_g=None,
    fats_g=None,
    remaining_fat_pct=40,
    remaining_carb_pct=60,
) -> dict:
    if entry_mode == MacroEntryMode.PERCENT:
        if macro_template and macro_template != MacroTemplate.CUSTOM and protein_pct is None:
            protein_pct, carbs_pct, fats_pct = apply_macro_template(macro_template)
        result = macros_from_percent(
            calories=calorie_target,
            protein_pct=protein_pct,
            carbs_pct=carbs_pct,
            fats_pct=fats_pct,
        )
        result["macro_entry_mode"] = entry_mode
        result["macro_template"] = macro_template or MacroTemplate.CUSTOM
        return result

    if entry_mode == MacroEntryMode.PROTEIN_FIRST:
        if protein_g is None:
            raise ValidationError({"protein_g": "Protein grams are required for protein-first mode."})
        result = macros_protein_first(
            calories=calorie_target,
            protein_g=protein_g,
            remaining_fat_pct=remaining_fat_pct,
            remaining_carb_pct=remaining_carb_pct,
        )
        result["macro_entry_mode"] = entry_mode
        result["macro_template"] = MacroTemplate.CUSTOM
        return result

    if entry_mode == MacroEntryMode.CUSTOM_GRAMS:
        if protein_g is None or carbs_g is None or fats_g is None:
            raise ValidationError({"macros": "protein_g, carbs_g, and fats_g are required."})
        p, c, f = _d(protein_g), _d(carbs_g), _d(fats_g)
        cal = _d(calorie_target) or Decimal("1")
        return {
            "macro_entry_mode": entry_mode,
            "macro_template": MacroTemplate.CUSTOM,
            "protein_g": p.quantize(Q1),
            "carbs_g": c.quantize(Q1),
            "fats_g": f.quantize(Q1),
            "protein_pct": ((p * 4 / cal) * 100).quantize(Q2),
            "carbs_pct": ((c * 4 / cal) * 100).quantize(Q2),
            "fats_pct": ((f * 9 / cal) * 100).quantize(Q2),
        }

    raise ValidationError({"macro_entry_mode": "Unsupported macro entry mode."})
