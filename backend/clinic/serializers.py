from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from .models import (
    Assessment,
    DoctorNote,
    FollowUpRecord,
    LabTestEntry,
    MounjaroDose,
    NutritionPlan,
    Patient,
    ProgressEntry,
)
from .utils import appointment_alert_active

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "phone", "full_name", "role")
        read_only_fields = fields


class PatientRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=200)
    age = serializers.IntegerField(min_value=1, max_value=120)
    gender = serializers.ChoiceField(choices=Patient.Gender.choices)
    phone = serializers.CharField(max_length=20)
    occupation = serializers.CharField(max_length=120, required=False, allow_blank=True)
    visit_date = serializers.DateTimeField()
    password = serializers.RegexField(
        regex=r"^\d{4,}$",
        error_messages={"invalid": "Password must be numeric (at least 4 digits)."},
    )

    def validate_phone(self, value):
        phone = value.strip()
        if User.objects.filter(phone=phone).exists() or User.objects.filter(username=phone).exists():
            raise serializers.ValidationError("Phone number is already registered.")
        return phone

    def validate_visit_date(self, value):
        if value < timezone.now() - timezone.timedelta(minutes=5):
            raise serializers.ValidationError("Visit date cannot be in the past.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        full_name = validated_data["full_name"].strip()
        parts = full_name.split(None, 2)
        first = parts[0] if parts else full_name
        middle = parts[1] if len(parts) > 1 else ""
        last = parts[2] if len(parts) > 2 else ""

        phone = validated_data["phone"]
        password = validated_data["password"]

        user = User.objects.create_user(
            username=phone,
            password=password,
            phone=phone,
            full_name=full_name,
            role=User.Role.PATIENT,
        )
        patient = Patient.objects.create(
            user=user,
            first_name=first,
            middle_name=middle,
            last_name=last,
            age=validated_data["age"],
            gender=validated_data["gender"],
            occupation=validated_data.get("occupation", ""),
        )
        Assessment.objects.create(
            patient=patient,
            visit_date=validated_data["visit_date"],
            checked_in=False,
        )
        NutritionPlan.objects.create(patient=patient)
        FollowUpRecord.objects.create(patient=patient)
        return patient


class PatientListSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="user.phone", read_only=True)
    full_name = serializers.CharField(source="display_name", read_only=True)
    visit_date = serializers.DateTimeField(source="assessment.visit_date", read_only=True, allow_null=True)
    checked_in = serializers.BooleanField(source="assessment.checked_in", read_only=True, default=False)
    is_submitted = serializers.BooleanField(source="assessment.is_submitted", read_only=True, default=False)
    alert = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = (
            "id",
            "file_number",
            "full_name",
            "phone",
            "age",
            "gender",
            "occupation",
            "visit_date",
            "checked_in",
            "is_submitted",
            "alert",
            "created_at",
        )

    def get_alert(self, obj):
        assessment = getattr(obj, "assessment", None)
        if not assessment:
            return False
        now = self.context.get("now") or timezone.now()
        return appointment_alert_active(assessment.visit_date, assessment.checked_in, now)


class AssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assessment
        fields = (
            "id",
            "weight",
            "height",
            "waist",
            "hip",
            "bmi",
            "bmi_class",
            "whr",
            "whr_class",
            "medical_history",
            "medications",
            "supplements",
            "lifestyle_notes",
            "sport_days_per_week",
            "activity_level",
            "sleep_hours",
            "stress_level",
            "eating_habits",
            "goal",
            "visit_date",
            "checked_in",
            "is_submitted",
            "updated_at",
        )
        read_only_fields = (
            "bmi",
            "bmi_class",
            "whr",
            "whr_class",
            "activity_level",
            "updated_at",
        )


class NutritionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionPlan
        fields = (
            "id",
            "daily_calories",
            "protein_pct",
            "carbs_pct",
            "fat_pct",
            "notes",
            "base_calories",
            "suggested_calories",
            "updated_at",
        )
        read_only_fields = ("base_calories", "suggested_calories", "updated_at")


class FollowUpRecordSerializer(serializers.ModelSerializer):
    estimated_next_visit = serializers.SerializerMethodField()

    class Meta:
        model = FollowUpRecord
        fields = (
            "id",
            "lab_results",
            "diet_system",
            "injections",
            "medications_text",
            "fat_dissolving_sessions",
            "next_followup_value",
            "next_followup_unit",
            "estimated_next_visit",
            "updated_at",
        )
        read_only_fields = ("estimated_next_visit", "updated_at")

    def get_estimated_next_visit(self, obj):
        if not obj.next_followup_value or not obj.updated_at:
            return None
        delta = timezone.timedelta(
            days=obj.next_followup_value
            if obj.next_followup_unit == FollowUpRecord.UNIT_DAY
            else obj.next_followup_value * 7
        )
        return (obj.updated_at + delta).isoformat()


class ProgressEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProgressEntry
        fields = ("id", "date", "weight", "bmi", "notes", "adherence", "created_at")
        read_only_fields = ("bmi", "created_at")


class MounjaroDoseSerializer(serializers.ModelSerializer):
    class Meta:
        model = MounjaroDose
        fields = ("id", "date", "weight", "dose", "notes", "created_at")
        read_only_fields = ("created_at",)


class LabTestEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestEntry
        fields = ("id", "date", "results", "notes", "created_at")
        read_only_fields = ("created_at",)


class DoctorNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorNote
        fields = ("id", "note", "created_at")
        read_only_fields = ("created_at",)


class PatientDetailSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(source="user.phone", read_only=True)
    full_name = serializers.CharField(source="display_name", read_only=True)
    assessment = AssessmentSerializer(read_only=True)
    nutrition_plan = NutritionPlanSerializer(read_only=True)
    follow_up = FollowUpRecordSerializer(read_only=True)
    progress_entries = ProgressEntrySerializer(many=True, read_only=True)
    mounjaro_doses = MounjaroDoseSerializer(many=True, read_only=True)
    lab_entries = LabTestEntrySerializer(many=True, read_only=True)
    doctor_notes = DoctorNoteSerializer(many=True, read_only=True)
    alert = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = (
            "id",
            "file_number",
            "full_name",
            "first_name",
            "middle_name",
            "last_name",
            "phone",
            "age",
            "gender",
            "occupation",
            "address",
            "assessment",
            "nutrition_plan",
            "follow_up",
            "progress_entries",
            "mounjaro_doses",
            "lab_entries",
            "doctor_notes",
            "alert",
            "created_at",
        )

    def get_alert(self, obj):
        assessment = getattr(obj, "assessment", None)
        if not assessment:
            return False
        return appointment_alert_active(
            assessment.visit_date, assessment.checked_in, timezone.now()
        )


class AppointmentSerializer(serializers.Serializer):
    visit_date = serializers.DateTimeField()

    def update(self, instance, validated_data):
        instance.visit_date = validated_data["visit_date"]
        instance.checked_in = False
        instance.save(update_fields=["visit_date", "checked_in", "updated_at"])
        return instance


class LoginSerializer(serializers.Serializer):
    """Supports phone (patients) or email (staff)."""

    identifier = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs["identifier"].strip()
        password = attrs["password"]
        user = (
            User.objects.filter(phone=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
            or User.objects.filter(username=identifier).first()
        )
        if not user or not user.check_password(password):
            raise serializers.ValidationError("Invalid login credentials.")
        if not user.is_active:
            raise serializers.ValidationError("Account is inactive.")
        attrs["user"] = user
        return attrs
