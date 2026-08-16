from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import UserProfile, WeightLog
from apps.accounts.serializers import (
    RegisterSerializer,
    TdeePreviewSerializer,
    UserProfileCreateSerializer,
    UserProfileSerializer,
    WeightLogSerializer,
)
from apps.accounts.services.tdee import calculate_daily_targets


def _profile_targets(*, weight_kg, height_cm, age, gender, activity_level) -> dict[str, int]:
    result = calculate_daily_targets(
        weight_kg=weight_kg,
        height_cm=height_cm,
        age=age,
        gender=gender,
        activity_level=activity_level,
        deficit=0 if int(age) < 18 else 500,
    )
    return {
        "target_calories": int(result["target_calories"]),
        "target_protein": int(result["target_protein"]),
        "target_carbs": int(result["target_carbs"]),
        "target_fats": int(result["target_fats"]),
    }


class RegisterView(APIView):
    """Create a new user account with profile and return JWT tokens."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        profile = user.profile
        targets = _profile_targets(
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            age=profile.age,
            gender=profile.gender,
            activity_level=profile.activity_level,
        )
        for key, value in targets.items():
            setattr(profile, key, value)
        profile.save(update_fields=list(targets.keys()))

        refresh = RefreshToken.for_user(user)
        tdee = calculate_daily_targets(
            weight_kg=profile.weight_kg,
            height_cm=profile.height_cm,
            age=profile.age,
            gender=profile.gender,
            activity_level=profile.activity_level,
        )
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "phone": user.username,
                },
                "profile": UserProfileSerializer(profile).data,
                "tdee": tdee,
            },
            status=status.HTTP_201_CREATED,
        )


class TdeePreviewView(APIView):
    """Preview BMR/TDEE and macro targets before creating a patient account."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        serializer = TdeePreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        result = calculate_daily_targets(
            weight_kg=data["weight_kg"],
            height_cm=data["height_cm"],
            age=data["age"],
            gender=data["gender"],
            activity_level=data.get(
                "activity_level",
                UserProfile.ActivityLevel.MODERATELY_ACTIVE,
            ),
            deficit=data.get("deficit", 0),
        )
        return Response(result)


class MyProfileView(APIView):
    """GET/POST/PATCH the authenticated user's nutrition profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Complete your profile to view daily targets."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(UserProfileSerializer(profile).data)

    def post(self, request: Request) -> Response:
        if hasattr(request.user, "profile"):
            return Response(
                {"detail": "Profile already exists."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserProfileCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        targets = _profile_targets(
            weight_kg=data["weight_kg"],
            height_cm=data["height_cm"],
            age=data["age"],
            gender=data["gender"],
            activity_level=data.get(
                "activity_level",
                UserProfile.ActivityLevel.SEDENTARY,
            ),
        )
        for key, value in targets.items():
            data.setdefault(key, value)

        profile = UserProfile.objects.create(user=request.user, **data)
        return Response(
            UserProfileSerializer(profile).data,
            status=status.HTTP_201_CREATED,
        )

    def patch(self, request: Request) -> Response:
        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Complete your profile to view daily targets."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class WeightLogView(APIView):
    """List / add weight check-ins and sync current profile weight."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        logs = WeightLog.objects.filter(user=request.user)[:60]
        return Response(WeightLogSerializer(logs, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = WeightLogSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        log = WeightLog.objects.create(user=request.user, **serializer.validated_data)
        try:
            profile = request.user.profile
            profile.weight_kg = log.weight_kg
            if profile.starting_weight_kg is None:
                profile.starting_weight_kg = log.weight_kg
            profile.save(update_fields=["weight_kg", "starting_weight_kg", "updated_at"])
            from apps.mealplans.services.weekly import apply_weight_loss_daily_targets

            apply_weight_loss_daily_targets(request.user)
        except UserProfile.DoesNotExist:
            pass
        return Response(WeightLogSerializer(log).data, status=status.HTTP_201_CREATED)
