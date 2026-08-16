from __future__ import annotations

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserProfile
from apps.mealplans.services.weekly import build_weekly_plan
from apps.subscriptions.models import Subscription


class WeeklyMealPlanView(APIView):
    """Return the scaled 7-day / 5-meal program for an active subscriber."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        now = timezone.now()
        subscription = (
            Subscription.objects.filter(
                user=request.user,
                status=Subscription.Status.ACTIVE,
                ends_at__gt=now,
            )
            .select_related("plan")
            .order_by("-ends_at")
            .first()
        )
        if not subscription:
            return Response(
                {
                    "detail": "Subscription required to view weekly meals.",
                    "code": "subscription_required",
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            profile = request.user.profile
        except UserProfile.DoesNotExist:
            return Response(
                {"detail": "Complete your profile first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        plan = build_weekly_plan(
            profile=profile,
            variety_level=subscription.plan.meal_variety_level,
        )
        plan["subscription"] = {
            "id": subscription.id,
            "ends_at": subscription.ends_at,
            "plan_code": subscription.plan.code,
            "variety_level": subscription.plan.meal_variety_level,
        }
        return Response(plan)
