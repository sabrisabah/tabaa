from __future__ import annotations

from rest_framework import filters, status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.foods.models import FoodItem
from apps.foods.serializers import FoodItemSerializer
from apps.foods.services.search import search_food_items


class FoodSearchView(APIView):
    """
    GET /api/foods/search/?search_terms=chicken

    Searches the local master database first. When no local matches exist,
    fetches from OpenFoodFacts, caches products locally, and returns them.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        query = (request.query_params.get("search_terms") or "").strip()

        if len(query) < 2:
            return Response(
                {"detail": "Provide at least 2 characters in search_terms."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        items, source = search_food_items(query, limit=20)
        serializer = FoodItemSerializer(items, many=True)

        return Response(
            {
                "search_terms": query,
                "source": source,
                "count": len(serializer.data),
                "results": serializer.data,
            }
        )


class FoodItemViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only browse/detail over cached master food data."""

    permission_classes = [IsAuthenticated]
    serializer_class = FoodItemSerializer
    queryset = FoodItem.objects.filter(is_active=True)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["name", "brand", "barcode"]
    ordering_fields = ["name", "calories"]
    ordering = ["name"]
