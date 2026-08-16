from django.contrib import admin

from apps.foods.models import FoodItem


@admin.register(FoodItem)
class FoodItemAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "calories", "protein", "carbs", "fats", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "brand", "barcode")
    readonly_fields = ("created_at", "updated_at")
