from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.mealplans.models import MealSlot, WeeklyMealTemplate
from apps.subscriptions.models import SubscriptionPlan

# Fixed weekly menu (variety_level=1). Same dishes each week; portions scale by calories.
WEEKLY_MENU = [
    # day, slot, title_ar, title_en, desc_ar, desc_en, kcal, P, C, F, portion_ar, portion_en
    (1, MealSlot.BREAKFAST, "بيض أومليت بالسبانخ", "Spinach omelette", "أومليت بيضتين + بياض مع سبانخ وطماطم", "2 eggs + 1 white with spinach & tomato", 280, 22, 8, 18, "حصة بيض كاملة", "1 egg serving"),
    (1, MealSlot.SNACK_1, "زبادي يوناني + لوز", "Greek yogurt + almonds", "علبة زبادي يوناني 100غ مع قبضة لوز", "100g Greek yogurt + handful almonds", 310, 16, 8, 22, "علبة صغيرة + حصة لوز", "Small tub + almond serving"),
    (1, MealSlot.LUNCH, "تكة دجاج مشوية", "Chicken tikka", "دجاج متبل زبادي وبهارات ليمون مع خبز ريف", "Yogurt-spiced chicken with one village bread slice", 420, 40, 25, 14, "100غ دجاج + شريحة خبز", "100g chicken + 1 bread slice"),
    (1, MealSlot.SNACK_2, "تفاح + راشي", "Apple + tahini", "حبة تفاح متوسطة مع ملعقة راشي", "Medium apple + 1 tbsp tahini", 170, 3, 28, 8, "حبة + ملعقة", "1 fruit + 1 spoon"),
    (1, MealSlot.DINNER, "سمك مشوي مع سلطة", "Grilled fish & salad", "فيليه سمك بالليمون مع خضار ورقية وزيت زيتون", "Lemon fish fillet with greens & olive oil", 380, 35, 12, 20, "120غ سمك + ملعقة زيت", "120g fish + 1 oil spoon"),
    (2, MealSlot.BREAKFAST, "بيض مسلوق مع أفوكادو", "Boiled eggs & avocado", "حصة بيض مع نصف أفوكادو", "Egg serving with ½ avocado", 370, 20, 10, 28, "حصة بيض + نصف أفوكادو", "Egg serving + ½ avocado"),
    (2, MealSlot.SNACK_1, "زبادي يوناني كبير", "Large Greek yogurt", "علبة 200غ بدون إضافات سكرية", "200g tub, no sugary add-ins", 300, 20, 10, 16, "علبة كبيرة", "Large tub"),
    (2, MealSlot.LUNCH, "دجاج مشوي بابريكا", "Paprika grilled chicken", "دجاج ملح فلفل بابريكا مع نصف كوب رز", "Salt-pepper-paprika chicken with ½ cup rice", 430, 38, 32, 12, "100غ دجاج + نصف كوب رز", "100g chicken + ½ cup rice"),
    (2, MealSlot.SNACK_2, "برتقال + فستق", "Orange + pistachios", "برتقالة مع حصة فستق 30غ", "1 orange + 30g pistachios", 220, 6, 18, 13, "حبة + حصة فستق", "1 fruit + pistachio serving"),
    (2, MealSlot.DINNER, "كفتة لحم بالفرن", "Oven kofta", "كفتة مشوية مع سلطة خضار", "Baked kofta with vegetable salad", 400, 30, 15, 24, "100غ لحم", "100g red meat"),
    (3, MealSlot.BREAKFAST, "أومليت خضار", "Veggie omelette", "بيض مع فلفل وبصل وطماطم ورشة بخاخ زيت", "Eggs with pepper, onion, tomato", 260, 20, 10, 16, "حصة بيض", "Egg serving"),
    (3, MealSlot.SNACK_1, "زبادي + بذور شيا", "Yogurt + chia", "زبادي 100غ مع 30غ بذور شيا", "100g yogurt + 30g chia", 295, 14, 18, 16, "علبة صغيرة + حصة شيا", "Small tub + chia serving"),
    (3, MealSlot.LUNCH, "دجاج بالكاري", "Curry chicken", "دجاج بصوص لبن وكاري مع بطاطا متوسطة", "Chicken in yogurt-curry sauce with medium potato", 450, 38, 35, 16, "100غ دجاج + حبة بطاطا", "100g chicken + 1 potato"),
    (3, MealSlot.SNACK_2, "فراولة + جوز", "Strawberries + walnuts", "كوب ونصف فراولة مع 30غ جوز", "1½ cups strawberries + 30g walnuts", 260, 5, 18, 20, "حصة فاكهة + جوز", "Fruit + walnut serving"),
    (3, MealSlot.DINNER, "ستيك لحم مشوي", "Grilled steak", "ستيك مع سلطة وزيت زيتون", "Steak with salad & olive oil", 420, 32, 8, 28, "100غ لحم + ملعقة زيت", "100g meat + oil spoon"),
    (4, MealSlot.BREAKFAST, "زبادي يوناني وفراولة", "Yogurt & strawberries", "علبة كبيرة مع حصة فراولة", "Large yogurt + strawberry serving", 360, 22, 25, 16, "علبة كبيرة + فاكهة", "Large tub + fruit"),
    (4, MealSlot.SNACK_1, "لوز وبذور قرع", "Almonds & pumpkin seeds", "حصة لوز + حصة بذور قرع", "Almond + pumpkin seed servings", 325, 12, 10, 28, "حصتين دهون صحية", "2 healthy-fat servings"),
    (4, MealSlot.LUNCH, "شاورما دجاج منزلية", "Homemade chicken shawarma", "دجاج مع صوص لبن وليمون وشريحة خبز ريف", "Chicken with yogurt-lemon sauce + bread", 440, 40, 28, 16, "100غ دجاج + خبز", "100g chicken + bread"),
    (4, MealSlot.SNACK_2, "رقي + زيتون", "Watermelon + olives", "كوب رقي مع 10–15 زيتونة", "1 cup watermelon + 10–15 olives", 150, 2, 16, 9, "حصة فاكهة + زيتون", "Fruit + olives"),
    (4, MealSlot.DINNER, "سلمون مشوي", "Grilled salmon", "سلمون مع خضار مشوية", "Salmon with roasted vegetables", 430, 35, 10, 26, "120غ سمك", "120g fish"),
    (5, MealSlot.BREAKFAST, "بيض مع زيت زيتون", "Eggs with olive oil", "أومليت بسيط مع ملعقة زيت زيتون", "Simple omelette + 1 olive oil spoon", 340, 18, 4, 28, "حصة بيض + زيت", "Egg serving + oil"),
    (5, MealSlot.SNACK_1, "زبادي يوناني + راشي", "Greek yogurt + tahini", "علبة 100غ مع ملعقة راشي", "100g yogurt + tahini spoon", 240, 12, 8, 16, "علبة صغيرة + راشي", "Small tub + tahini"),
    (5, MealSlot.LUNCH, "دجاج مع خضار طاجن", "Chicken vegetable tagine", "دجاج مع فلفل وكوسا (بدون بروكلي عند اضطراب الغدة)", "Chicken with pepper & zucchini (skip broccoli if thyroid issue)", 400, 38, 12, 18, "100غ دجاج + خضار", "100g chicken + veg"),
    (5, MealSlot.SNACK_2, "أفوكادو", "Avocado", "نصف حبة أفوكادو", "½ avocado", 160, 2, 8, 15, "نصف حبة", "Half fruit"),
    (5, MealSlot.DINNER, "تونة بالماء مع سلطة", "Tuna salad", "تونة مع زيت زيتون وخضار ورقية", "Tuna with olive oil & greens", 360, 35, 6, 22, "حصة سمك معلب + زيت", "Fish serving + oil"),
    (6, MealSlot.BREAKFAST, "بيض مسلوق وزيتون", "Boiled eggs & olives", "حصة بيض مع زيتون غير منزوع النوى", "Egg serving + whole olives", 300, 18, 4, 22, "بيض + 10–15 زيتونة", "Eggs + olives"),
    (6, MealSlot.SNACK_1, "لبنة خفيفة مع جوز", "Labneh-style yogurt & walnuts", "زبادي كثيف مع حصة جوز", "Thick yogurt + walnut serving", 350, 14, 8, 28, "زبادي + جوز", "Yogurt + walnuts"),
    (6, MealSlot.LUNCH, "مرق لحم بالخضار", "Meat stew with vegetables", "مرق لحم مع بامية أو فاصوليا خضراء", "Meat stew with okra or green beans", 420, 30, 18, 24, "100غ لحم", "100g meat"),
    (6, MealSlot.SNACK_2, "بذور شيا منقوعة", "Soaked chia", "حصة بذور شيا مع ماء أو لبن خفيف", "30g chia soaked", 145, 5, 12, 9, "30غ", "30g"),
    (6, MealSlot.DINNER, "دجاج بالطماطم والبصل", "Chicken with tomato & onion", "طاجن دجاج بسيط قليل الكارب", "Simple low-carb chicken bake", 380, 38, 10, 18, "100غ دجاج", "100g chicken"),
    (7, MealSlot.BREAKFAST, "أومليت فلفل وبصل", "Pepper & onion omelette", "بيض مع إضافات حسب الرغبة", "Eggs with preferred add-ins", 270, 20, 8, 16, "حصة بيض", "Egg serving"),
    (7, MealSlot.SNACK_1, "زبادي يوناني + فستق", "Yogurt + pistachios", "علبة صغيرة مع حصة فستق", "Small yogurt + pistachios", 310, 14, 10, 20, "زبادي + فستق", "Yogurt + pistachios"),
    (7, MealSlot.LUNCH, "برغر منزلي بدون خبز", "Homemade burger (no bun)", "لحم مفروم مشوي مع سلطة وأفوكادو", "Grilled minced meat with salad & avocado", 480, 32, 12, 34, "100غ لحم + نصف أفوكادو", "100g meat + ½ avocado"),
    (7, MealSlot.SNACK_2, "تفاح صغير", "Small apple", "حبة فاكهة مسموحة", "Allowed fruit serving", 80, 0, 25, 0, "حبة متوسطة", "Medium fruit"),
    (7, MealSlot.DINNER, "شوربة دجاج وخضار", "Chicken vegetable soup", "دجاج مسلوق مع خضار مختلفة", "Boiled chicken with mixed vegetables", 340, 32, 14, 14, "حصة دجاج في شوربة", "Chicken in soup"),
]


class Command(BaseCommand):
    help = "Seed subscription plans and the fixed weekly meal program."

    def handle(self, *args, **options):
        monthly, _ = SubscriptionPlan.objects.update_or_create(
            code="monthly",
            defaults={
                "name_ar": "اشتراك شهري",
                "name_en": "Monthly subscription",
                "price_iqd": 25000,
                "duration_days": 30,
                "meal_variety_level": 1,
                "is_active": True,
            },
        )
        multi, _ = SubscriptionPlan.objects.update_or_create(
            code="quarterly",
            defaults={
                "name_ar": "اشتراك 3 أشهر (تنوع أكثر)",
                "name_en": "3-month plan (more variety)",
                "price_iqd": 70000,
                "duration_days": 90,
                "meal_variety_level": 2,
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Plans ready: {monthly.code}, {multi.code}"))

        created = 0
        for row in WEEKLY_MENU:
            (
                day,
                slot,
                title_ar,
                title_en,
                desc_ar,
                desc_en,
                kcal,
                protein,
                carbs,
                fats,
                portion_ar,
                portion_en,
            ) = row
            sort_map = {
                MealSlot.BREAKFAST: 1,
                MealSlot.SNACK_1: 2,
                MealSlot.LUNCH: 3,
                MealSlot.SNACK_2: 4,
                MealSlot.DINNER: 5,
            }
            _, was_created = WeeklyMealTemplate.objects.update_or_create(
                day_of_week=day,
                meal_slot=slot,
                variety_level=1,
                defaults={
                    "title_ar": title_ar,
                    "title_en": title_en,
                    "description_ar": desc_ar,
                    "description_en": desc_en,
                    "base_calories": kcal,
                    "base_protein_g": Decimal(str(protein)),
                    "base_carbs_g": Decimal(str(carbs)),
                    "base_fats_g": Decimal(str(fats)),
                    "base_portion_note_ar": portion_ar,
                    "base_portion_note_en": portion_en,
                    "sort_order": sort_map.get(slot, 0),
                    "is_active": True,
                },
            )
            if was_created:
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Weekly menu templates upserted ({created} newly created)."
            )
        )
