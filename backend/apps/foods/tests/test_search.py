from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from apps.foods.models import FoodItem
from apps.foods.services.search import (
    import_foods_from_openfoodfacts,
    search_food_items,
    search_local_food_items,
)


class FoodSearchServiceTests(TestCase):
    def setUp(self):
        FoodItem.objects.create(
            name="Greek Yogurt",
            brand="Fage",
            calories=Decimal("100"),
            protein=Decimal("17"),
            carbs=Decimal("6"),
            fats=Decimal("0"),
            fiber=Decimal("0"),
            serving_size=Decimal("170"),
            serving_unit="g",
        )

    def test_search_local_food_items(self):
        results = search_local_food_items("yogurt")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Greek Yogurt")

    @patch("apps.foods.services.search._fetch_openfoodfacts_products")
    def test_search_falls_back_to_openfoodfacts(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "code": "1234567890123",
                "product_name": "Protein Bar",
                "brands": "FitBrand",
                "serving_quantity": "60",
                "serving_unit": "g",
                "nutriments": {
                    "energy-kcal_serving": 220,
                    "proteins_serving": 20,
                    "carbohydrates_serving": 22,
                    "fat_serving": 8,
                    "fiber_serving": 3,
                },
            }
        ]

        results, source = search_food_items("protein bar")
        self.assertEqual(source, "openfoodfacts")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "Protein Bar")
        self.assertEqual(results[0].barcode, "1234567890123")

        # Cached locally on second search
        cached, source = search_food_items("protein bar")
        self.assertEqual(source, "local")
        self.assertEqual(len(cached), 1)


class FoodSearchViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="demo", password="demo12345")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_search_requires_min_length(self):
        response = self.client.get("/api/foods/search/", {"search_terms": "a"})
        self.assertEqual(response.status_code, 400)

    @patch("apps.foods.services.search.search_food_items")
    def test_search_endpoint_returns_results(self, mock_search):
        food = FoodItem.objects.create(
            name="Banana",
            calories=Decimal("89"),
            protein=Decimal("1"),
            carbs=Decimal("23"),
            fats=Decimal("0"),
            fiber=Decimal("3"),
            serving_size=Decimal("100"),
            serving_unit="g",
        )
        mock_search.return_value = ([food], "local")

        response = self.client.get("/api/foods/search/", {"search_terms": "banana"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["source"], "local")
        self.assertEqual(response.data["results"][0]["name"], "Banana")
