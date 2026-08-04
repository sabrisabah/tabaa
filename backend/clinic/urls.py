from django.urls import path

from . import views

urlpatterns = [
    path("info/", views.clinic_info, name="clinic-info"),
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="login"),
    path("auth/me/", views.MeView.as_view(), name="me"),
    path("patients/", views.PatientListCreateView.as_view(), name="patients"),
    path("patients/me/", views.MyPatientView.as_view(), name="my-patient"),
    path("patients/<int:pk>/", views.PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<int:pk>/assessment/", views.AssessmentUpdateView.as_view()),
    path("patients/<int:pk>/nutrition/", views.NutritionPlanUpdateView.as_view()),
    path("patients/<int:pk>/follow-up/", views.FollowUpUpdateView.as_view()),
    path("patients/<int:pk>/progress/", views.ProgressListCreateView.as_view()),
    path("patients/<int:patient_id>/progress/<int:pk>/", views.ProgressDeleteView.as_view()),
    path("patients/<int:pk>/mounjaro/", views.MounjaroListCreateView.as_view()),
    path("patients/<int:patient_id>/mounjaro/<int:pk>/", views.MounjaroDeleteView.as_view()),
    path("patients/<int:pk>/labs/", views.LabListCreateView.as_view()),
    path("patients/<int:patient_id>/labs/<int:pk>/", views.LabDeleteView.as_view()),
    path("patients/<int:pk>/notes/", views.DoctorNoteListCreateView.as_view()),
    path("patients/<int:patient_id>/notes/<int:pk>/", views.DoctorNoteDeleteView.as_view()),
    path("patients/<int:pk>/appointment/", views.AppointmentUpdateView.as_view()),
    path("patients/<int:pk>/check-in/", views.CheckInView.as_view()),
]
