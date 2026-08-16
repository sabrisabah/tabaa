from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.diary.views import DailyDiaryViewSet, MealLogViewSet

router = DefaultRouter()
router.register(r"diary", DailyDiaryViewSet, basename="diary")
router.register(r"meal-logs", MealLogViewSet, basename="meal-log")

urlpatterns = [
    path("", include(router.urls)),
]
