from __future__ import annotations

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class UserProfile(models.Model):
    """
    Extended nutrition profile linked one-to-one with Django's built-in User.

    Target macros are stored here after backend TDEE/goal calculations.
    """

    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"
        OTHER = "other", "Other"

    class ActivityLevel(models.TextChoices):
        SEDENTARY = "sedentary", "Sedentary (little or no exercise)"
        LIGHTLY_ACTIVE = "lightly_active", "Lightly active (1-3 days/week)"
        MODERATELY_ACTIVE = "moderately_active", "Moderately active (3-5 days/week)"
        VERY_ACTIVE = "very_active", "Very active (6-7 days/week)"
        EXTRA_ACTIVE = "extra_active", "Extra active (physical job or 2x training)"

    class ClinicRole(models.TextChoices):
        PATIENT = "patient", "Patient"
        SECRETARY = "secretary", "Secretary"
        DOCTOR = "doctor", "Doctor / Manager"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    clinic_role = models.CharField(
        max_length=20,
        choices=ClinicRole.choices,
        default=ClinicRole.PATIENT,
        help_text="Clinic access role for د. طيبة staff and patients.",
    )
    patient_file_number = models.CharField(
        max_length=32,
        blank=True,
        default="",
        help_text="Clinic patient file number (displayed on invoices).",
    )
    allergies = models.TextField(blank=True, default="")
    disliked_foods = models.TextField(blank=True, default="")
    diagnoses = models.TextField(blank=True, default="")
    active_medications = models.TextField(blank=True, default="")
    clinical_goal = models.CharField(max_length=255, blank=True, default="")
    safety_alerts = models.TextField(blank=True, default="")
    show_tdee_calculator = models.BooleanField(
        default=False,
        help_text="When enabled by the doctor, the patient can see the TDEE calculator in the app.",
    )

    weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(1), MaxValueValidator(500)],
    )
    height_cm = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(50), MaxValueValidator(300)],
    )
    age = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(120)],
        help_text="Age in completed years. Under 18 uses paediatric nutrition pathway.",
    )
    gender = models.CharField(max_length=10, choices=Gender.choices)
    activity_level = models.CharField(
        max_length=20,
        choices=ActivityLevel.choices,
        default=ActivityLevel.SEDENTARY,
    )

    # Daily targets — populated by the nutrition service layer
    target_calories = models.PositiveIntegerField(default=2000)
    target_protein = models.PositiveIntegerField(
        default=150,
        help_text="Daily protein target in grams.",
    )
    target_carbs = models.PositiveIntegerField(
        default=200,
        help_text="Daily carbohydrate target in grams.",
    )
    target_fats = models.PositiveIntegerField(
        default=65,
        help_text="Daily fat target in grams.",
    )

    full_name = models.CharField(max_length=120, blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    gps_latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    gps_longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
    )
    starting_weight_kg = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Weight at program start — used for loss progress / gift tracking.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"Profile for {self.user.get_username()}"


class WeightLog(models.Model):
    """Body-weight check-ins for progress / gift tracking."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="weight_logs",
    )
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    recorded_at = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-recorded_at", "-created_at"]

    def __str__(self) -> str:
        return f"{self.user} · {self.weight_kg} kg · {self.recorded_at}"
