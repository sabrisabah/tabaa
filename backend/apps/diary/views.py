from __future__ import annotations

from django.db import IntegrityError
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import UserProfile
from apps.diary.models import DailyDiary, MealLog
from apps.diary.serializers import (
    DailyDiaryListSerializer,
    DailyDiarySerializer,
    MealLogSerializer,
    TodaySummarySerializer,
)
from apps.diary.services.summary import build_today_summary_payload


class DailyDiaryViewSet(viewsets.ModelViewSet):
    """
    CRUD for the authenticated user's daily diaries.

    Nested meal logs are included on retrieve; use MealLogViewSet to mutate entries.
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            DailyDiary.objects.filter(user=self.request.user)
            .prefetch_related("meal_logs__food_item")
            .order_by("-date")
        )

    def get_serializer_class(self):
        if self.action == "list":
            return DailyDiaryListSerializer
        return DailyDiarySerializer

    def create(self, request: Request, *args, **kwargs) -> Response:
        """
        Idempotent create: return the existing diary when (user, date) already exists.
        Prevents IntegrityError from concurrent login/dashboard loads.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        diary_date = serializer.validated_data.get("date") or timezone.localdate()
        notes = serializer.validated_data.get("notes", "")

        try:
            diary, created = DailyDiary.objects.get_or_create(
                user=request.user,
                date=diary_date,
                defaults={"notes": notes},
            )
        except IntegrityError:
            diary = DailyDiary.objects.get(user=request.user, date=diary_date)
            created = False

        output = DailyDiarySerializer(diary, context=self.get_serializer_context())
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"], url_path="today")
    def today(self, request: Request) -> Response:
        """GET /api/diary/today/ — get or create today's diary with meal logs."""
        today = timezone.localdate()
        try:
            diary, _ = DailyDiary.objects.get_or_create(
                user=request.user,
                date=today,
                defaults={"notes": ""},
            )
        except IntegrityError:
            diary = DailyDiary.objects.get(user=request.user, date=today)

        diary = (
            DailyDiary.objects.filter(pk=diary.pk)
            .prefetch_related("meal_logs__food_item")
            .get()
        )
        serializer = DailyDiarySerializer(diary, context=self.get_serializer_context())
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="today/summary")
    def today_summary(self, request: Request) -> Response:
        """
        GET /api/diary/today/summary/

        Returns today's consumed macros (quantity × food nutrition via DB aggregate)
        alongside the user's target values from UserProfile.
        """
        today = timezone.localdate()

        try:
            payload = build_today_summary_payload(request.user, today)
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Complete your profile to view daily targets."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = TodaySummarySerializer(payload)
        return Response(serializer.data)


class MealLogViewSet(viewsets.ModelViewSet):
    """CRUD for meal log entries belonging to the authenticated user's diaries."""

    permission_classes = [IsAuthenticated]
    serializer_class = MealLogSerializer

    def get_queryset(self):
        queryset = (
            MealLog.objects.filter(daily_diary__user=self.request.user)
            .select_related("food_item", "daily_diary")
            .order_by("-created_at")
        )

        diary_id = self.request.query_params.get("daily_diary")
        if diary_id is not None:
            queryset = queryset.filter(daily_diary_id=diary_id)

        meal_type = self.request.query_params.get("meal_type")
        if meal_type is not None:
            queryset = queryset.filter(meal_type=meal_type)

        return queryset

    def perform_create(self, serializer):
        daily_diary = serializer.validated_data["daily_diary"]
        if daily_diary.user_id != self.request.user.pk:
            # Defensive; serializer validation should already enforce ownership.
            raise PermissionDenied("Cannot log meals to another user's diary.")
        serializer.save()
