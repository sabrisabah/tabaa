from django.db import migrations, models


def rename_english_brand(apps, schema_editor):
    ClinicSettings = apps.get_model("billing", "ClinicSettings")
    ClinicSettings.objects.filter(pk=1).update(clinic_name_en="Dr. Teeba")


def restore_english_brand(apps, schema_editor):
    ClinicSettings = apps.get_model("billing", "ClinicSettings")
    ClinicSettings.objects.filter(pk=1).update(clinic_name_en="Dr. Taybah")


class Migration(migrations.Migration):
    dependencies = [
        ("billing", "0002_rename_clinic_brand"),
    ]

    operations = [
        migrations.AlterField(
            model_name="clinicsettings",
            name="clinic_name_en",
            field=models.CharField(default="Dr. Teeba", max_length=120),
        ),
        migrations.RunPython(rename_english_brand, restore_english_brand),
    ]
