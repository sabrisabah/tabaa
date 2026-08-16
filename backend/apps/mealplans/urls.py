from django.urls import path

from apps.mealplans.clinical_views import (
    EnergyPreviewView,
    MacroPreviewView,
    MyNutritionPlanView,
    NutritionPlanApproveView,
    NutritionPlanArchiveView,
    NutritionPlanDetailView,
    NutritionPlanListCreateView,
    NutritionPlanReviseView,
)
from apps.mealplans.views import WeeklyMealPlanView

urlpatterns = [
    path("meal-plans/weekly/", WeeklyMealPlanView.as_view(), name="meal-plan-weekly"),
    path("nutrition-plans/energy-preview/", EnergyPreviewView.as_view(), name="nutrition-energy-preview"),
    path("nutrition-plans/macro-preview/", MacroPreviewView.as_view(), name="nutrition-macro-preview"),
    path("nutrition-plans/", NutritionPlanListCreateView.as_view(), name="nutrition-plans"),
    path("nutrition-plans/mine/", MyNutritionPlanView.as_view(), name="nutrition-plans-mine"),
    path("nutrition-plans/<int:pk>/", NutritionPlanDetailView.as_view(), name="nutrition-plan-detail"),
    path("nutrition-plans/<int:pk>/approve/", NutritionPlanApproveView.as_view(), name="nutrition-plan-approve"),
    path("nutrition-plans/<int:pk>/revise/", NutritionPlanReviseView.as_view(), name="nutrition-plan-revise"),
    path("nutrition-plans/<int:pk>/archive/", NutritionPlanArchiveView.as_view(), name="nutrition-plan-archive"),
]
