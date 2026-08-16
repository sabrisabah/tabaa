from __future__ import annotations

import json
import logging
import re
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.db.models import Q

from apps.foods.models import FoodItem

logger = logging.getLogger(__name__)

OPENFOODFACTS_SEARCH_URL = "https://world.openfoodfacts.org/api/v2/search"
OPENFOODFACTS_USER_AGENT = "NutritionTracker/1.0 (Django; contact@example.com)"
MIN_LOCAL_RESULTS_BEFORE_OFF = 1  # Fall back to OFF when local search is empty


def search_local_food_items(query: str, *, limit: int = 20) -> list[FoodItem]:
    """Search the master FoodItem table (case-insensitive)."""
    normalized = query.strip()
    if not normalized:
        return []

    return list(
        FoodItem.objects.filter(is_active=True)
        .filter(
            Q(name__icontains=normalized)
            | Q(brand__icontains=normalized)
            | Q(barcode__icontains=normalized)
        )
        .order_by("name")[:limit]
    )


def search_food_items(query: str, *, limit: int = 20) -> tuple[list[FoodItem], str]:
    """
    Search foods locally first. If nothing is found, fetch from OpenFoodFacts,
    cache results in FoodItem, and return the imported rows.

    Returns (items, source) where source is ``local`` or ``openfoodfacts``.
    """
    local_results = search_local_food_items(query, limit=limit)
    if len(local_results) >= MIN_LOCAL_RESULTS_BEFORE_OFF:
        return local_results, "local"

    imported = import_foods_from_openfoodfacts(query, limit=limit)
    return imported, "openfoodfacts"


def import_foods_from_openfoodfacts(query: str, *, limit: int = 20) -> list[FoodItem]:
    """Fetch products from OpenFoodFacts and upsert them into FoodItem."""
    products = _fetch_openfoodfacts_products(query, page_size=limit)
    saved: list[FoodItem] = []

    for product in products:
        parsed = _parse_openfoodfacts_product(product)
        if parsed is None:
            continue

        item = _upsert_food_item(parsed)
        if item is not None:
            saved.append(item)

    return saved


def _fetch_openfoodfacts_products(query: str, *, page_size: int) -> list[dict[str, Any]]:
    params = urlencode(
        {
            "search_terms": query.strip(),
            "page_size": page_size,
            "fields": (
                "code,product_name,brands,nutriments,"
                "serving_size,serving_quantity,serving_unit,quantity"
            ),
        }
    )
    url = f"{OPENFOODFACTS_SEARCH_URL}?{params}"
    request = Request(url, headers={"User-Agent": OPENFOODFACTS_USER_AGENT})

    try:
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("OpenFoodFacts search failed for query=%r: %s", query, exc)
        return []

    products = payload.get("products") or []
    return products if isinstance(products, list) else []


def _parse_openfoodfacts_product(product: dict[str, Any]) -> dict[str, Any] | None:
    name = (product.get("product_name") or "").strip()
    if not name:
        return None

    nutriments = product.get("nutriments") or {}
    serving_size, serving_unit = _resolve_serving(product)

    calories = _pick_nutrient(nutriments, "energy-kcal", serving_size)
    protein = _pick_nutrient(nutriments, "proteins", serving_size)
    carbs = _pick_nutrient(nutriments, "carbohydrates", serving_size)
    fats = _pick_nutrient(nutriments, "fat", serving_size)
    fiber = _pick_nutrient(nutriments, "fiber", serving_size)

    if calories <= 0 and protein <= 0 and carbs <= 0 and fats <= 0:
        return None

    barcode = _normalize_barcode(product.get("code"))
    brand = (product.get("brands") or "").split(",")[0].strip()

    return {
        "name": name[:255],
        "brand": brand[:255],
        "barcode": barcode,
        "calories": max(calories, Decimal("0")),
        "protein": max(protein, Decimal("0")),
        "carbs": max(carbs, Decimal("0")),
        "fats": max(fats, Decimal("0")),
        "fiber": max(fiber, Decimal("0")),
        "serving_size": serving_size,
        "serving_unit": serving_unit[:32],
    }


def _resolve_serving(product: dict[str, Any]) -> tuple[Decimal, str]:
    """Determine serving size/unit from OpenFoodFacts payload."""
    serving_unit = (product.get("serving_unit") or "").strip() or "g"

    if product.get("serving_quantity") is not None:
        try:
            qty = Decimal(str(product["serving_quantity"]))
            if qty > 0:
                return qty.quantize(Decimal("0.01")), serving_unit
        except (InvalidOperation, TypeError):
            pass

    serving_size_raw = (product.get("serving_size") or product.get("quantity") or "").strip()
    if serving_size_raw:
        parsed_qty, parsed_unit = _parse_serving_text(serving_size_raw)
        if parsed_qty is not None:
            return parsed_qty, parsed_unit

    return Decimal("100"), "g"


_SERVING_PATTERN = re.compile(
    r"^\s*([0-9]+(?:[.,][0-9]+)?)\s*([a-zA-Z]+)?\s*$",
)


def _parse_serving_text(value: str) -> tuple[Decimal | None, str]:
    match = _SERVING_PATTERN.match(value)
    if not match:
        return None, "g"

    try:
        qty = Decimal(match.group(1).replace(",", ".")).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None, "g"

    unit = (match.group(2) or "g").lower()
    return qty, unit


def _pick_nutrient(nutriments: dict[str, Any], base_key: str, serving_size: Decimal) -> Decimal:
    """
    Prefer per-serving nutrients; fall back to per-100g scaled by serving size.
    """
    serving_key = f"{base_key}_serving"
    per100_key = f"{base_key}_100g"

    if nutriments.get(serving_key) is not None:
        return _to_decimal(nutriments[serving_key])

    if nutriments.get(per100_key) is not None:
        per100 = _to_decimal(nutriments[per100_key])
        return (per100 * serving_size / Decimal("100")).quantize(Decimal("0.01"))

    if base_key == "energy-kcal":
        for key in ("energy-kcal", "energy-kcal_100g"):
            if nutriments.get(key) is not None:
                per100 = _to_decimal(nutriments[key])
                return (per100 * serving_size / Decimal("100")).quantize(Decimal("0.01"))

    return Decimal("0")


def _to_decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError):
        return Decimal("0")


def _normalize_barcode(code: Any) -> str | None:
    if code is None:
        return None
    barcode = str(code).strip()
    return barcode or None


def _upsert_food_item(data: dict[str, Any]) -> FoodItem | None:
    """Insert or update a FoodItem, keyed by barcode when available."""
    barcode = data.get("barcode")

    if barcode:
        item, _created = FoodItem.objects.update_or_create(
            barcode=barcode,
            defaults={
                "name": data["name"],
                "brand": data["brand"],
                "calories": data["calories"],
                "protein": data["protein"],
                "carbs": data["carbs"],
                "fats": data["fats"],
                "fiber": data["fiber"],
                "serving_size": data["serving_size"],
                "serving_unit": data["serving_unit"],
                "is_active": True,
            },
        )
        return item

    return FoodItem.objects.create(
        name=data["name"],
        brand=data["brand"],
        barcode=None,
        calories=data["calories"],
        protein=data["protein"],
        carbs=data["carbs"],
        fats=data["fats"],
        fiber=data["fiber"],
        serving_size=data["serving_size"],
        serving_unit=data["serving_unit"],
        is_active=True,
    )
