from __future__ import annotations

from rest_framework import serializers

from apps.subscriptions.models import Subscription, SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = (
            "id",
            "code",
            "name_ar",
            "name_en",
            "price_iqd",
            "duration_days",
            "meal_variety_level",
        )


class SubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)
    is_access_granted = serializers.BooleanField(read_only=True)

    class Meta:
        model = Subscription
        fields = (
            "id",
            "plan",
            "status",
            "payment_reference",
            "amount_iqd",
            "superqi_transaction_id",
            "paid_at",
            "activated_at",
            "starts_at",
            "ends_at",
            "is_access_granted",
            "created_at",
        )


class SubscribeSerializer(serializers.Serializer):
    plan_code = serializers.SlugField(required=False, default="monthly")


class ConfirmTransferSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=120)
    address = serializers.CharField(max_length=255)
    gps_latitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    gps_longitude = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
    )
    subscription_id = serializers.IntegerField(required=False)
