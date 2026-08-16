from __future__ import annotations

from rest_framework.permissions import BasePermission

from apps.accounts.models import UserProfile


def get_clinic_role(user) -> str:
    if not user or not user.is_authenticated:
        return ""
    if user.is_superuser:
        return UserProfile.ClinicRole.DOCTOR
    try:
        return user.profile.clinic_role
    except UserProfile.DoesNotExist:
        return UserProfile.ClinicRole.PATIENT


class IsClinicStaff(BasePermission):
    """Doctor or secretary."""

    def has_permission(self, request, view) -> bool:
        return get_clinic_role(request.user) in {
            UserProfile.ClinicRole.DOCTOR,
            UserProfile.ClinicRole.SECRETARY,
        }


class IsDoctor(BasePermission):
    def has_permission(self, request, view) -> bool:
        return get_clinic_role(request.user) == UserProfile.ClinicRole.DOCTOR


class IsSecretaryOrDoctor(BasePermission):
    def has_permission(self, request, view) -> bool:
        return get_clinic_role(request.user) in {
            UserProfile.ClinicRole.DOCTOR,
            UserProfile.ClinicRole.SECRETARY,
        }
