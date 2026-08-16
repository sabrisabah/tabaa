from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.foods.views import FoodItemViewSet, FoodSearchView

router = DefaultRouter()
router.register(r"foods", FoodItemViewSet, basename="food")

urlpatterns = [
    path("foods/search/", FoodSearchView.as_view(), name="food-search"),
    path("", include(router.urls)),
]
