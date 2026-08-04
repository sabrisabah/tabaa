def calculate_bmi(weight, height_cm):
    if not weight or not height_cm or height_cm <= 0:
        return None, ""
    height_m = height_cm / 100.0
    bmi = round(weight / (height_m * height_m), 1)
    return bmi, classify_bmi(bmi)


def classify_bmi(bmi):
    if bmi is None:
        return ""
    if bmi < 18.5:
        return "Underweight"
    if bmi < 25:
        return "Normal"
    if bmi < 30:
        return "Overweight"
    if bmi < 35:
        return "Obesity class 1"
    if bmi < 40:
        return "Obesity class 2"
    return "Obesity class 3"


def calculate_whr(waist, hip, gender=""):
    if not waist or not hip or hip <= 0:
        return None, ""
    whr = round(waist / hip, 2)
    return whr, classify_whr(whr, gender)


def classify_whr(whr, gender=""):
    if whr is None:
        return ""
    g = (gender or "").lower()
    if g == "male":
        if whr < 0.90:
            return "Low risk"
        if whr < 1.0:
            return "Moderate risk"
        return "High risk"
    # female / default
    if whr < 0.80:
        return "Low risk"
    if whr < 0.85:
        return "Moderate risk"
    return "High risk"


def activity_level_from_days(days):
    if days is None:
        return ""
    if days <= 0:
        return "sedentary"
    if days <= 2:
        return "light"
    if days <= 4:
        return "moderate"
    if days <= 6:
        return "active"
    return "very_active"


ACTIVITY_MULTIPLIER = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def calculate_calories(weight, height, age, gender, activity_level, goal):
    """Mifflin-St Jeor based suggestion."""
    if not all([weight, height, age]):
        return None, None
    g = (gender or "").lower()
    if g == "male":
        bmr = 10 * weight + 6.25 * height - 5 * age + 5
    else:
        bmr = 10 * weight + 6.25 * height - 5 * age - 161

    multiplier = ACTIVITY_MULTIPLIER.get(activity_level or "sedentary", 1.2)
    tdee = bmr * multiplier
    base = int(round(tdee))

    goal = (goal or "maintain").lower()
    if goal == "lose":
        suggested = int(round(tdee - 500))
    elif goal == "gain":
        suggested = int(round(tdee + 300))
    else:
        suggested = base

    return max(base, 1000), max(suggested, 1000)


def appointment_alert_active(visit_date, checked_in, now):
    if checked_in or not visit_date:
        return False
    delta_seconds = (visit_date - now).total_seconds()
    return delta_seconds <= 3600
