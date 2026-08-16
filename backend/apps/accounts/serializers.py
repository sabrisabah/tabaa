from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from apps.accounts.models import UserProfile, WeightLog
from apps.accounts.phone import validate_iraq_phone

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    phone = serializers.CharField(max_length=20)
    password = serializers.CharField(write_only=True, style={"input_type": "password"})
    password_confirm = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )
    gender = serializers.ChoiceField(choices=UserProfile.Gender.choices)
    age = serializers.IntegerField(min_value=1, max_value=120)
    height_cm = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=50, max_value=300)
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=1, max_value=500)
    activity_level = serializers.ChoiceField(
        choices=UserProfile.ActivityLevel.choices,
        required=False,
        default=UserProfile.ActivityLevel.MODERATELY_ACTIVE,
    )

    def validate_phone(self, value: str) -> str:
        try:
            phone = validate_iraq_phone(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        if User.objects.filter(username=phone).exists():
            raise serializers.ValidationError(
                "An account with this phone number already exists.",
            )
        return phone

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Passwords do not match."},
            )
        password = attrs["password"]
        if not password.isdigit() or len(password) != 4:
            raise serializers.ValidationError(
                {"password": "Password must be exactly 4 digits."},
            )
        validate_password(password)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirm")
        phone = validated_data.pop("phone")
        password = validated_data.pop("password")
        profile_data = {
            "gender": validated_data.pop("gender"),
            "age": validated_data.pop("age"),
            "height_cm": validated_data.pop("height_cm"),
            "weight_kg": validated_data.pop("weight_kg"),
            "activity_level": validated_data.pop(
                "activity_level",
                UserProfile.ActivityLevel.MODERATELY_ACTIVE,
            ),
        }

        user = User.objects.create_user(username=phone, email="", password=password)
        UserProfile.objects.create(user=user, **profile_data)
        return user


class TdeePreviewSerializer(serializers.Serializer):
    gender = serializers.ChoiceField(choices=UserProfile.Gender.choices)
    age = serializers.IntegerField(min_value=1, max_value=120)
    height_cm = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=50, max_value=300)
    weight_kg = serializers.DecimalField(max_digits=6, decimal_places=2, min_value=1, max_value=500)
    activity_level = serializers.ChoiceField(
        choices=UserProfile.ActivityLevel.choices,
        required=False,
        default=UserProfile.ActivityLevel.MODERATELY_ACTIVE,
    )
    deficit = serializers.IntegerField(required=False, min_value=0, max_value=1000, default=0)

class PhoneTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Authenticate with Iraqi phone number (07XXXXXXXXX) instead of username."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("username", None)
        self.fields["phone"] = serializers.CharField()

    def validate(self, attrs):
        try:
            phone = validate_iraq_phone(attrs.pop("phone", ""))
        except ValueError as exc:
            raise serializers.ValidationError({"phone": str(exc)}) from exc

        attrs[self.username_field] = phone
        data = super().validate(attrs)
        data["phone"] = phone
        return data


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for reading and updating a user's nutrition profile."""

    phone = serializers.CharField(source="user.username", read_only=True)
    user_id = serializers.IntegerField(source="user.id", read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id",
            "user_id",
            "phone",
            "clinic_role",
            "patient_file_number",
            "full_name",
            "address",
            "gps_latitude",
            "gps_longitude",
            "starting_weight_kg",
            "weight_kg",
            "height_cm",
            "age",
            "gender",
            "activity_level",
            "allergies",
            "disliked_foods",
            "diagnoses",
            "active_medications",
            "clinical_goal",
            "safety_alerts",
            "show_tdee_calculator",
            "target_calories",
            "target_protein",
            "target_carbs",
            "target_fats",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "phone",
            "clinic_role",
            "show_tdee_calculator",
            "created_at",
            "updated_at",
        ]


class UserProfileCreateSerializer(serializers.ModelSerializer):
    """Used to create the authenticated user's nutrition profile."""

    class Meta:
        model = UserProfile
        fields = [
            "full_name",
            "address",
            "weight_kg",
            "height_cm",
            "age",
            "gender",
            "activity_level",
            "target_calories",
            "target_protein",
            "target_carbs",
            "target_fats",
        ]
        extra_kwargs = {
            "full_name": {"required": False},
            "address": {"required": False},
            "target_calories": {"required": False},
            "target_protein": {"required": False},
            "target_carbs": {"required": False},
            "target_fats": {"required": False},
            "activity_level": {"required": False},
        }


class WeightLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeightLog
        fields = ("id", "weight_kg", "note", "recorded_at", "created_at")
        read_only_fields = ("id", "created_at")
