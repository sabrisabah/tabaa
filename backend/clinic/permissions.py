from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsDoctor(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "doctor"
        )


class IsSecretary(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "secretary"
        )


class IsDoctorOrSecretary(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in ("doctor", "secretary")
        )


class IsPatient(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == "patient"
        )


class IsDoctorOrReadOnlyPatientOwner(BasePermission):
    """Doctor full access; patient can read own data."""

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.role == "doctor":
            return True
        if user.role == "secretary" and request.method in SAFE_METHODS:
            return True
        if user.role == "patient":
            patient = getattr(obj, "patient", obj)
            return getattr(patient, "user_id", None) == user.id and request.method in SAFE_METHODS
        return False
