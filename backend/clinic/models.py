from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Max

from .utils import (
    activity_level_from_days,
    calculate_bmi,
    calculate_calories,
    calculate_whr,
    classify_bmi,
    classify_whr,
)


class User(AbstractUser):
    class Role(models.TextChoices):
        PATIENT = "patient", "Patient"
        DOCTOR = "doctor", "Doctor"
        SECRETARY = "secretary", "Secretary"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.PATIENT)
    phone = models.CharField(max_length=20, blank=True, unique=True, null=True)
    full_name = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.full_name or self.username or self.email or str(self.pk)


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="patient_profile"
    )
    file_number = models.CharField(max_length=20, unique=True, blank=True)
    first_name = models.CharField(max_length=80, blank=True)
    middle_name = models.CharField(max_length=80, blank=True)
    last_name = models.CharField(max_length=80, blank=True)
    address = models.CharField(max_length=255, blank=True)
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    occupation = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.file_number} — {self.display_name}"

    @property
    def display_name(self):
        parts = [self.first_name, self.middle_name, self.last_name]
        name = " ".join(p for p in parts if p).strip()
        return name or self.user.full_name or self.user.username

    def save(self, *args, **kwargs):
        if not self.file_number:
            self.file_number = self._next_file_number()
        super().save(*args, **kwargs)

    @classmethod
    def _next_file_number(cls):
        prefix = getattr(settings, "FILE_NUMBER_PREFIX", "TAIBA")
        last = (
            cls.objects.filter(file_number__startswith=f"{prefix}-")
            .aggregate(Max("file_number"))
            .get("file_number__max")
        )
        next_num = 1
        if last:
            try:
                next_num = int(last.split("-")[-1]) + 1
            except (ValueError, IndexError):
                next_num = cls.objects.count() + 1
        return f"{prefix}-{next_num:04d}"


class Assessment(models.Model):
    class Goal(models.TextChoices):
        LOSE = "lose", "Lose weight"
        MAINTAIN = "maintain", "Maintain weight"
        GAIN = "gain", "Gain weight"

    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name="assessment")
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    waist = models.FloatField(null=True, blank=True)
    hip = models.FloatField(null=True, blank=True)
    bmi = models.FloatField(null=True, blank=True)
    bmi_class = models.CharField(max_length=50, blank=True)
    whr = models.FloatField(null=True, blank=True)
    whr_class = models.CharField(max_length=50, blank=True)

    medical_history = models.TextField(blank=True)
    medications = models.TextField(blank=True)
    supplements = models.TextField(blank=True)
    lifestyle_notes = models.TextField(blank=True)
    sport_days_per_week = models.PositiveIntegerField(null=True, blank=True)
    activity_level = models.CharField(max_length=40, blank=True)
    sleep_hours = models.FloatField(null=True, blank=True)
    stress_level = models.CharField(max_length=40, blank=True)
    eating_habits = models.TextField(blank=True)
    goal = models.CharField(max_length=20, choices=Goal.choices, blank=True)

    visit_date = models.DateTimeField(null=True, blank=True)
    checked_in = models.BooleanField(default=False)
    is_submitted = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def recompute(self):
        self.bmi, self.bmi_class = calculate_bmi(self.weight, self.height)
        self.whr, self.whr_class = calculate_whr(self.waist, self.hip, self.patient.gender)
        self.activity_level = activity_level_from_days(self.sport_days_per_week)

    def save(self, *args, **kwargs):
        self.recompute()
        super().save(*args, **kwargs)


class NutritionPlan(models.Model):
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name="nutrition_plan")
    daily_calories = models.PositiveIntegerField(null=True, blank=True)
    protein_pct = models.FloatField(null=True, blank=True)
    carbs_pct = models.FloatField(null=True, blank=True)
    fat_pct = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    base_calories = models.PositiveIntegerField(null=True, blank=True)
    suggested_calories = models.PositiveIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def refresh_suggestions(self):
        assessment = getattr(self.patient, "assessment", None)
        if not assessment:
            return
        base, suggested = calculate_calories(
            weight=assessment.weight,
            height=assessment.height,
            age=self.patient.age,
            gender=self.patient.gender,
            activity_level=assessment.activity_level,
            goal=assessment.goal,
        )
        self.base_calories = base
        self.suggested_calories = suggested


class FollowUpRecord(models.Model):
    UNIT_DAY = "day"
    UNIT_WEEK = "week"
    UNIT_CHOICES = [(UNIT_DAY, "Day"), (UNIT_WEEK, "Week")]

    INJECTION_CHOICES = [
        ("b12", "Vitamin B12"),
        ("vit_d", "Vitamin D"),
        ("iron", "Iron"),
        ("glutathione", "Glutathione"),
        ("other", "Other"),
    ]

    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name="follow_up")
    lab_results = models.JSONField(default=dict, blank=True)
    diet_system = models.TextField(blank=True)
    injections = models.JSONField(default=list, blank=True)
    medications_text = models.TextField(blank=True)
    fat_dissolving_sessions = models.BooleanField(default=False)
    next_followup_value = models.PositiveIntegerField(null=True, blank=True)
    next_followup_unit = models.CharField(
        max_length=10, choices=UNIT_CHOICES, default=UNIT_WEEK, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)


class ProgressEntry(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="progress_entries")
    date = models.DateField()
    weight = models.FloatField()
    bmi = models.FloatField(null=True, blank=True)
    notes = models.TextField(blank=True)
    adherence = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]

    def save(self, *args, **kwargs):
        assessment = getattr(self.patient, "assessment", None)
        height = assessment.height if assessment else None
        bmi, _ = calculate_bmi(self.weight, height)
        self.bmi = bmi
        super().save(*args, **kwargs)


class MounjaroDose(models.Model):
    DOSE_CHOICES = [
        (2.5, "2.5 mg"),
        (5.0, "5 mg"),
        (7.5, "7.5 mg"),
        (10.0, "10 mg"),
        (12.5, "12.5 mg"),
        (15.0, "15 mg"),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="mounjaro_doses")
    date = models.DateField()
    weight = models.FloatField(null=True, blank=True)
    dose = models.FloatField(choices=DOSE_CHOICES)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class LabTestEntry(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="lab_entries")
    date = models.DateField()
    results = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]


class DoctorNote(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="doctor_notes")
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


# Standard monthly lab keys (HOMA-IR first)
DEFAULT_LAB_KEYS = [
    "HOMA-IR",
    "Glucose",
    "Insulin",
    "HbA1c",
    "Cholesterol",
    "LDL",
    "HDL",
    "Triglycerides",
    "ALT",
    "AST",
    "Creatinine",
    "Urea",
    "Vitamin D",
    "B12",
    "Ferritin",
    "TSH",
    "T3",
    "T4",
    "CBC",
]
