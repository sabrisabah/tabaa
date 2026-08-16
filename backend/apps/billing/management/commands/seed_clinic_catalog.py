from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.billing.models import ClinicService, ClinicSettings, ServiceCategory, ServicePriceVariant


SERVICES = [
    {
        "code": "doctor_visit",
        "name_ar": "كشفية الطبيب",
        "name_en": "Doctor visit",
        "category": ServiceCategory.CONSULTATION,
        "unit_label_ar": "تستوفى لمرة واحدة، والمتابعة مجانية",
        "base_price_iqd": 25_000,
        "is_doctor_visit": True,
        "sort_order": 1,
    },
    {
        "code": "free_follow_up",
        "name_ar": "متابعة مجانية",
        "name_en": "Free follow-up",
        "category": ServiceCategory.FOLLOW_UP,
        "unit_label_ar": "توثيق زيارة بدون إيراد",
        "base_price_iqd": 0,
        "is_free_follow_up": True,
        "sort_order": 2,
    },
    {
        "code": "online_consult",
        "name_ar": "استشارة أونلاين",
        "name_en": "Online consultation",
        "category": ServiceCategory.CONSULTATION,
        "unit_label_ar": "لكل استشارة أونلاين",
        "base_price_iqd": 50_000,
        "sort_order": 3,
    },
    {
        "code": "inbody",
        "name_ar": "فحص جهاز InBody",
        "name_en": "InBody scan",
        "category": ServiceCategory.LAB,
        "unit_label_ar": "لكل فحص",
        "base_price_iqd": 15_000,
        "sort_order": 4,
    },
    {
        "code": "nutrition_plan",
        "name_ar": "إعداد النظام الغذائي",
        "name_en": "Nutrition plan preparation",
        "category": ServiceCategory.NUTRITION,
        "unit_label_ar": "لكل نظام غذائي",
        "base_price_iqd": 25_000,
        "sort_order": 5,
    },
    {
        "code": "fat_dissolve",
        "name_ar": "جلسة تذويب الدهون",
        "name_en": "Fat dissolving session",
        "category": ServiceCategory.INJECTION,
        "unit_label_ar": "لكل إبرة؛ الكمية قابلة للتغيير",
        "base_price_iqd": 150_000,
        "allow_quantity": True,
        "sort_order": 6,
    },
    {
        "code": "iv_nutrient",
        "name_ar": "جلسة مغذٍ وريدي",
        "name_en": "IV nutrient session",
        "category": ServiceCategory.INJECTION,
        "unit_label_ar": "لكل جلسة",
        "base_price_iqd": 250_000,
        "sort_order": 7,
    },
    {
        "code": "anti_aging",
        "name_ar": "جلسة مضاد الشيخوخة",
        "name_en": "Anti-aging session",
        "category": ServiceCategory.INJECTION,
        "unit_label_ar": "لكل جلسة",
        "base_price_iqd": 300_000,
        "sort_order": 8,
    },
    {
        "code": "iron_session",
        "name_ar": "جلسة الحديد",
        "name_en": "Iron session",
        "category": ServiceCategory.INJECTION,
        "unit_label_ar": "لكل جلسة",
        "base_price_iqd": 100_000,
        "sort_order": 9,
    },
    {
        "code": "ozempic",
        "name_ar": "جرعة أوزمبك",
        "name_en": "Ozempic dose",
        "category": ServiceCategory.MEDICATION,
        "unit_label_ar": "لكل جرعة",
        "base_price_iqd": 50_000,
        "sort_order": 10,
    },
    {
        "code": "mounjaro",
        "name_ar": "جرعة مونجارو",
        "name_en": "Mounjaro dose",
        "category": ServiceCategory.MEDICATION,
        "unit_label_ar": "حسب الجرعة",
        "base_price_iqd": 150_000,
        "has_price_variants": True,
        "sort_order": 11,
    },
]

MOUNJARO_DOSES = [
    ("2_5_mg", "2.5 mg", 150_000),
    ("5_mg", "5 mg", 175_000),
    ("7_5_mg", "7.5 mg", 200_000),
    ("10_mg", "10 mg", 225_000),
    ("12_5_mg", "12.5 mg", 250_000),
    ("15_mg", "15 mg", 275_000),
]


class Command(BaseCommand):
    help = "Seed د. طيبة clinic services, Mounjaro doses, and clinic settings."

    def handle(self, *args, **options):
        settings = ClinicSettings.get_solo()
        settings.clinic_name_ar = "د. طيبة"
        settings.clinic_name_en = "Dr. Teeba"
        settings.save(update_fields=["clinic_name_ar", "clinic_name_en"])
        for row in SERVICES:
            defaults = {k: v for k, v in row.items() if k != "code"}
            obj, created = ClinicService.objects.update_or_create(
                code=row["code"],
                defaults=defaults,
            )
            self.stdout.write(f"{'Created' if created else 'Updated'} service {obj.code}")

        mounjaro = ClinicService.objects.get(code="mounjaro")
        for index, (code, label, price) in enumerate(MOUNJARO_DOSES):
            ServicePriceVariant.objects.update_or_create(
                service=mounjaro,
                code=code,
                defaults={
                    "label_ar": label,
                    "label_en": label,
                    "price_iqd": price,
                    "sort_order": index,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS("Clinic catalog seeded for د. طيبة."))
