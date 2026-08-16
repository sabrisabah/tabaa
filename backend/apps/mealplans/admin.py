from django.contrib import admin

from apps.mealplans.clinical_models import NutritionPlan, NutritionPlanVersion, PlanMealItem
from apps.mealplans.models import WeeklyMealTemplate


@admin.register(WeeklyMealTemplate)
class WeeklyMealTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "day_of_week",
        "meal_slot",
        "title_ar",
        "base_calories",
        "variety_level",
        "is_active",
    )
    list_filter = ("day_of_week", "meal_slot", "variety_level", "is_active")
    search_fields = ("title_ar", "title_en")


class PlanMealItemInline(admin.TabularInline):
    model = PlanMealItem
    extra = 0


class NutritionPlanVersionInline(admin.StackedInline):
    model = NutritionPlanVersion
    extra = 0
    show_change_link = True


@admin.register(NutritionPlan)
class NutritionPlanAdmin(admin.ModelAdmin):
    list_display = ("name", "patient", "status", "current_version", "is_paediatric_pathway", "updated_at")
    list_filter = ("status", "is_paediatric_pathway")
    search_fields = ("name", "patient__username")
    inlines = [NutritionPlanVersionInline]


@admin.register(NutritionPlanVersion)
class NutritionPlanVersionAdmin(admin.ModelAdmin):
    list_display = ("plan", "version_number", "calorie_target", "is_locked", "approved_at")
    inlines = [PlanMealItemInline]
