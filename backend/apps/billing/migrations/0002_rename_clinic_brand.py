from django.db import migrations, models


def rename_clinic_brand(apps, schema_editor):
    ClinicSettings = apps.get_model("billing", "ClinicSettings")
    ClinicSettings.objects.filter(pk=1).update(
        clinic_name_ar="د. طيبة",
        clinic_name_en="Dr. Taybah",
    )


def restore_clinic_brand(apps, schema_editor):
    ClinicSettings = apps.get_model("billing", "ClinicSettings")
    ClinicSettings.objects.filter(pk=1).update(
        clinic_name_ar="طيبه",
        clinic_name_en="Taybah",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="clinicsettings",
            name="clinic_name_ar",
            field=models.CharField(default="د. طيبة", max_length=120),
        ),
        migrations.AlterField(
            model_name="clinicsettings",
            name="clinic_name_en",
            field=models.CharField(default="Dr. Taybah", max_length=120),
        ),
        migrations.RunPython(rename_clinic_brand, restore_clinic_brand),
    ]
