from __future__ import annotations

from rest_framework import serializers

from apps.diary.models import DailyDiary, MealLog
from apps.foods.models import FoodItem
from apps.foods.serializers import FoodItemSerializer


class MealLogSerializer(serializers.ModelSerializer):
    """
    Meal log with nested read-only FoodItem so the frontend receives
    full nutrition data in a single request.

    On write, pass `food_item_id` (primary key). On read, `food_item` is expanded.
    """

    food_item = FoodItemSerializer(read_only=True)
    food_item_id = serializers.PrimaryKeyRelatedField(
        queryset=FoodItem.objects.filter(is_active=True),
        source="food_item",
        write_only=True,
    )

    def validate_daily_diary(self, value: DailyDiary) -> DailyDiary:
        request = self.context.get("request")
        if request and value.user_id != request.user.pk:
            raise serializers.ValidationError("This diary does not belong to you.")
        return value

    class Meta:
        model = MealLog
        fields = [
            "id",
            "daily_diary",
            "meal_type",
            "food_item",
            "food_item_id",
            "quantity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DailyDiarySerializer(serializers.ModelSerializer):
    """Daily diary with nested meal logs (each including food nutrition data)."""

    meal_logs = MealLogSerializer(many=True, read_only=True)

    class Meta:
        model = DailyDiary
        fields = [
            "id",
            "user",
            "date",
            "notes",
            "meal_logs",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "user", "created_at", "updated_at"]


class DailyDiaryListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for diary list views without nested meal logs."""

    meal_log_count = serializers.IntegerField(source="meal_logs.count", read_only=True)

    class Meta:
        model = DailyDiary
        fields = [
            "id",
            "user",
            "date",
            "notes",
            "meal_log_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class MacroTotalsSerializer(serializers.Serializer):
    calories = serializers.FloatField()
    protein = serializers.FloatField()
    carbs = serializers.FloatField()
    fats = serializers.FloatField()


class TodaySummarySerializer(serializers.Serializer):
    date = serializers.DateField()
    consumed = MacroTotalsSerializer()
    targets = MacroTotalsSerializer()
    remaining = MacroTotalsSerializer()
