from django.contrib import admin

from apps.accounts.models import UserProfile, WeightLog


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "clinic_role",
        "patient_file_number",
        "show_tdee_calculator",
        "weight_kg",
        "starting_weight_kg",
        "height_cm",
        "age",
        "gender",
        "activity_level",
        "target_calories",
    )
    list_filter = ("clinic_role", "show_tdee_calculator", "gender", "activity_level")
    list_editable = ("show_tdee_calculator",)
    search_fields = ("user__username", "full_name", "address", "patient_file_number")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("user", "clinic_role", "patient_file_number", "full_name", "address")}),
        ("Anthropometrics", {"fields": ("weight_kg", "height_cm", "age", "gender", "activity_level", "starting_weight_kg")}),
        (
            "Clinical context",
            {
                "fields": (
                    "clinical_goal",
                    "allergies",
                    "disliked_foods",
                    "diagnoses",
                    "active_medications",
                    "safety_alerts",
                    "show_tdee_calculator",
                ),
            },
        ),
        ("Targets", {"fields": ("target_calories", "target_protein", "target_carbs", "target_fats")}),
        ("Meta", {"fields": ("gps_latitude", "gps_longitude", "created_at", "updated_at")}),
    )


@admin.register(WeightLog)
class WeightLogAdmin(admin.ModelAdmin):
    list_display = ("user", "weight_kg", "recorded_at", "created_at")
    search_fields = ("user__username",)
    list_filter = ("recorded_at",)
