from django.contrib import admin

from apps.diary.models import DailyDiary, MealLog


class MealLogInline(admin.TabularInline):
    model = MealLog
    extra = 0
    readonly_fields = ("created_at", "updated_at")


@admin.register(DailyDiary)
class DailyDiaryAdmin(admin.ModelAdmin):
    list_display = ("user", "date", "created_at")
    list_filter = ("date",)
    search_fields = ("user__username",)
    inlines = [MealLogInline]
    readonly_fields = ("created_at", "updated_at")


@admin.register(MealLog)
class MealLogAdmin(admin.ModelAdmin):
    list_display = ("daily_diary", "meal_type", "food_item", "quantity", "created_at")
    list_filter = ("meal_type",)
    readonly_fields = ("created_at", "updated_at")
