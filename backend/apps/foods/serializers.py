from __future__ import annotations

from rest_framework import serializers

from apps.foods.models import FoodItem


class FoodItemSerializer(serializers.ModelSerializer):
    """Read-only serializer for master food data exposed to the frontend."""

    class Meta:
        model = FoodItem
        fields = [
            "id",
            "name",
            "brand",
            "barcode",
            "calories",
            "protein",
            "carbs",
            "fats",
            "fiber",
            "serving_size",
            "serving_unit",
            "is_active",
        ]
        read_only_fields = fields
