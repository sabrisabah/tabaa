from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from import_export import fields, resources
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from .models import (
    Assessment,
    DoctorNote,
    FollowUpRecord,
    LabTestEntry,
    MounjaroDose,
    NutritionPlan,
    Patient,
    ProgressEntry,
    User,
)


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "phone",
            "full_name",
            "role",
            "is_active",
            "password",
        )
        export_order = fields
        import_id_fields = ("id",)

    def dehydrate_password(self, obj):
        # Never export password hashes
        return ""

    def before_save_instance(self, instance, row, **kwargs):
        raw = row.get("password") if isinstance(row, dict) else None
        if raw:
            instance.set_password(str(raw))
        elif instance.pk:
            # Keep existing password when blank on import
            existing = User.objects.filter(pk=instance.pk).first()
            if existing:
                instance.password = existing.password


@admin.register(User)
class UserAdmin(ImportExportModelAdmin, DjangoUserAdmin):
    resource_classes = [UserResource]
    list_display = ("username", "email", "phone", "full_name", "role", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "email", "phone", "full_name")
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Taiba Clinic", {"fields": ("role", "phone", "full_name")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Taiba Clinic", {"fields": ("role", "phone", "full_name")}),
    )


class AssessmentResource(resources.ModelResource):
    patient = fields.Field(
        column_name="patient",
        attribute="patient",
        widget=ForeignKeyWidget(Patient, "file_number"),
    )

    class Meta:
        model = Assessment
        fields = (
            "id",
            "patient",
            "weight",
            "height",
            "waist",
            "hip",
            "medical_history",
            "medications",
            "supplements",
            "lifestyle_notes",
            "sport_days_per_week",
            "sleep_hours",
            "stress_level",
            "eating_habits",
            "goal",
            "visit_date",
            "checked_in",
            "is_submitted",
        )
        export_order = fields

    def before_save_instance(self, instance, row, **kwargs):
        # Recompute BMI/WHR/activity on server — ignore imported computed fields
        instance.recompute()


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("file_number", "display_name", "age", "gender", "user")
    search_fields = ("file_number", "first_name", "last_name", "user__phone", "user__full_name")


@admin.register(Assessment)
class AssessmentAdmin(ImportExportModelAdmin):
    resource_classes = [AssessmentResource]
    list_display = ("patient", "visit_date", "checked_in", "is_submitted", "bmi", "weight")
    search_fields = ("patient__file_number", "patient__first_name")


@admin.register(NutritionPlan)
class NutritionPlanAdmin(admin.ModelAdmin):
    list_display = ("patient", "daily_calories", "suggested_calories", "updated_at")


@admin.register(FollowUpRecord)
class FollowUpRecordAdmin(admin.ModelAdmin):
    list_display = ("patient", "next_followup_value", "next_followup_unit", "updated_at")


@admin.register(ProgressEntry)
class ProgressEntryAdmin(admin.ModelAdmin):
    list_display = ("patient", "date", "weight", "bmi")


@admin.register(MounjaroDose)
class MounjaroDoseAdmin(admin.ModelAdmin):
    list_display = ("patient", "date", "dose", "weight")


@admin.register(LabTestEntry)
class LabTestEntryAdmin(admin.ModelAdmin):
    list_display = ("patient", "date")


@admin.register(DoctorNote)
class DoctorNoteAdmin(admin.ModelAdmin):
    list_display = ("patient", "created_at")
