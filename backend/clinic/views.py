from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import (
    DEFAULT_LAB_KEYS,
    Assessment,
    DoctorNote,
    FollowUpRecord,
    LabTestEntry,
    MounjaroDose,
    NutritionPlan,
    Patient,
    ProgressEntry,
)
from .permissions import IsDoctor, IsDoctorOrSecretary, IsPatient
from .serializers import (
    AppointmentSerializer,
    AssessmentSerializer,
    DoctorNoteSerializer,
    FollowUpRecordSerializer,
    LabTestEntrySerializer,
    LoginSerializer,
    MounjaroDoseSerializer,
    NutritionPlanSerializer,
    PatientDetailSerializer,
    PatientListSerializer,
    PatientRegisterSerializer,
    ProgressEntrySerializer,
    UserSerializer,
)

User = get_user_model()


def tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        "refresh": str(refresh),
        "access": str(refresh.access_token),
        "user": UserSerializer(user).data,
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def clinic_info(request):
    return Response(
        {
            "name": settings.CLINIC_NAME,
            "brand": settings.CLINIC_BRAND,
            "file_prefix": settings.FILE_NUMBER_PREFIX,
            "lab_keys": DEFAULT_LAB_KEYS,
            "injections": [
                {"value": v, "label": l}
                for v, l in FollowUpRecord.INJECTION_CHOICES
            ],
        }
    )


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        # Force patient role — never allow doctor/secretary via public register
        serializer = PatientRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        return Response(
            {
                **tokens_for_user(patient.user),
                "patient": PatientListSerializer(
                    patient, context={"now": timezone.now()}
                ).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(tokens_for_user(serializer.validated_data["user"]))


class MeView(APIView):
    def get(self, request):
        data = UserSerializer(request.user).data
        if request.user.role == User.Role.PATIENT:
            patient = getattr(request.user, "patient_profile", None)
            if patient:
                data["patient"] = PatientDetailSerializer(patient).data
        return Response(data)


class PatientListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctorOrSecretary]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PatientRegisterSerializer
        return PatientListSerializer

    def get_queryset(self):
        qs = Patient.objects.select_related("user", "assessment").all()
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(
                models_q(q)
            )
        return qs

    def list(self, request, *args, **kwargs):
        now = timezone.now()
        qs = self.filter_queryset(self.get_queryset())
        # Sort: nearest / most overdue appointments first; no appointment at bottom
        patients = list(qs)

        def sort_key(p):
            a = getattr(p, "assessment", None)
            if not a or not a.visit_date:
                return (1, timezone.datetime.max.replace(tzinfo=timezone.utc))
            return (0, a.visit_date)

        patients.sort(key=sort_key)
        serializer = PatientListSerializer(patients, many=True, context={"now": now})
        upcoming = [
            s
            for s in serializer.data
            if s.get("visit_date")
            and timezone.datetime.fromisoformat(s["visit_date"].replace("Z", "+00:00"))
            > now
            and timezone.datetime.fromisoformat(s["visit_date"].replace("Z", "+00:00")).date()
            > now.date()
        ]
        upcoming.sort(key=lambda x: x["visit_date"])
        return Response({"patients": serializer.data, "upcoming": upcoming})

    def create(self, request, *args, **kwargs):
        serializer = PatientRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        patient = serializer.save()
        # Do NOT log in as the new patient — return credentials for secretary
        return Response(
            {
                "patient": PatientListSerializer(
                    patient, context={"now": timezone.now()}
                ).data,
                "credentials": {
                    "phone": patient.user.phone,
                    "password": request.data.get("password"),
                },
                "message": "Patient registered successfully. Share the login credentials with the patient.",
            },
            status=status.HTTP_201_CREATED,
        )


def models_q(q):
    from django.db.models import Q

    return (
        Q(file_number__icontains=q)
        | Q(first_name__icontains=q)
        | Q(middle_name__icontains=q)
        | Q(last_name__icontains=q)
        | Q(user__full_name__icontains=q)
        | Q(user__phone__icontains=q)
    )


class PatientDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PatientDetailSerializer
    queryset = Patient.objects.select_related(
        "user", "assessment", "nutrition_plan", "follow_up"
    ).prefetch_related(
        "progress_entries", "mounjaro_doses", "lab_entries", "doctor_notes"
    )

    def get_object(self):
        obj = super().get_object()
        user = self.request.user
        if user.role == User.Role.PATIENT and obj.user_id != user.id:
            self.permission_denied(self.request)
        if user.role not in (User.Role.DOCTOR, User.Role.SECRETARY, User.Role.PATIENT):
            self.permission_denied(self.request)
        return obj


class MyPatientView(APIView):
    permission_classes = [IsPatient]

    def get(self, request):
        patient = get_object_or_404(Patient, user=request.user)
        return Response(PatientDetailSerializer(patient).data)


class AssessmentUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_patient(self, pk):
        return get_object_or_404(Patient, pk=pk)

    def patch(self, request, pk):
        patient = self.get_patient(pk)
        user = request.user
        assessment, _ = Assessment.objects.get_or_create(patient=patient)

        if user.role == User.Role.PATIENT:
            if patient.user_id != user.id:
                return Response({"detail": "Permission denied."}, status=403)
            if assessment.is_submitted:
                return Response(
                    {"detail": "Form is locked. Only the doctor or secretary can edit it."},
                    status=403,
                )
            # Patients cannot change visit/check-in via this endpoint freely after submit
            data = {
                k: v
                for k, v in request.data.items()
                if k not in ("checked_in", "is_submitted")
            }
            serializer = AssessmentSerializer(assessment, data=data, partial=True)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save(is_submitted=True)
            return Response(AssessmentSerializer(obj).data)

        if user.role in (User.Role.DOCTOR, User.Role.SECRETARY):
            serializer = AssessmentSerializer(assessment, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            return Response(AssessmentSerializer(obj).data)

        return Response({"detail": "Permission denied."}, status=403)


class NutritionPlanUpdateView(APIView):
    permission_classes = [IsDoctor]

    def patch(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        plan, _ = NutritionPlan.objects.get_or_create(patient=patient)
        plan.refresh_suggestions()
        serializer = NutritionPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        obj.refresh_suggestions()
        obj.save(update_fields=["base_calories", "suggested_calories"])
        return Response(NutritionPlanSerializer(obj).data)

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        plan, _ = NutritionPlan.objects.get_or_create(patient=patient)
        plan.refresh_suggestions()
        plan.save(update_fields=["base_calories", "suggested_calories"])
        return Response(NutritionPlanSerializer(plan).data)


class FollowUpUpdateView(APIView):
    permission_classes = [IsDoctorOrSecretary]

    def patch(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        record, _ = FollowUpRecord.objects.get_or_create(patient=patient)
        serializer = FollowUpRecordSerializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(FollowUpRecordSerializer(serializer.save()).data)


class ProgressListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctor]
    serializer_class = ProgressEntrySerializer

    def get_queryset(self):
        return ProgressEntry.objects.filter(patient_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        patient = get_object_or_404(Patient, pk=self.kwargs["pk"])
        serializer.save(patient=patient)


class ProgressDeleteView(generics.DestroyAPIView):
    permission_classes = [IsDoctor]
    serializer_class = ProgressEntrySerializer

    def get_queryset(self):
        return ProgressEntry.objects.filter(patient_id=self.kwargs["patient_id"])


class MounjaroListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctor]
    serializer_class = MounjaroDoseSerializer

    def get_queryset(self):
        return MounjaroDose.objects.filter(patient_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        patient = get_object_or_404(Patient, pk=self.kwargs["pk"])
        serializer.save(patient=patient)


class MounjaroDeleteView(generics.DestroyAPIView):
    permission_classes = [IsDoctor]
    serializer_class = MounjaroDoseSerializer

    def get_queryset(self):
        return MounjaroDose.objects.filter(patient_id=self.kwargs["patient_id"])


class LabListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctor]
    serializer_class = LabTestEntrySerializer

    def get_queryset(self):
        return LabTestEntry.objects.filter(patient_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        patient = get_object_or_404(Patient, pk=self.kwargs["pk"])
        serializer.save(patient=patient)


class LabDeleteView(generics.DestroyAPIView):
    permission_classes = [IsDoctor]
    serializer_class = LabTestEntrySerializer

    def get_queryset(self):
        return LabTestEntry.objects.filter(patient_id=self.kwargs["patient_id"])


class DoctorNoteListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorNoteSerializer

    def get_queryset(self):
        return DoctorNote.objects.filter(patient_id=self.kwargs["pk"])

    def perform_create(self, serializer):
        patient = get_object_or_404(Patient, pk=self.kwargs["pk"])
        serializer.save(patient=patient)


class DoctorNoteDeleteView(generics.DestroyAPIView):
    permission_classes = [IsDoctor]
    serializer_class = DoctorNoteSerializer

    def get_queryset(self):
        return DoctorNote.objects.filter(patient_id=self.kwargs["patient_id"])


class AppointmentUpdateView(APIView):
    permission_classes = [IsDoctorOrSecretary]

    def patch(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        assessment, _ = Assessment.objects.get_or_create(patient=patient)
        serializer = AppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.update(assessment, serializer.validated_data)
        return Response(
            PatientListSerializer(patient, context={"now": timezone.now()}).data
        )


class CheckInView(APIView):
    permission_classes = [IsDoctorOrSecretary]

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        assessment, _ = Assessment.objects.get_or_create(patient=patient)
        assessment.checked_in = True
        assessment.save(update_fields=["checked_in", "updated_at"])
        return Response(
            PatientListSerializer(patient, context={"now": timezone.now()}).data
        )
