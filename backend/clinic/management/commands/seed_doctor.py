from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create the default doctor account for Dr. Taiba clinic"

    def handle(self, *args, **options):
        email = "doctor@taiba.clinic"
        password = "doctor123"
        user, created = User.objects.get_or_create(
            username="doctor",
            defaults={
                "email": email,
                "full_name": "Dr. Taiba",
                "role": User.Role.DOCTOR,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.SUCCESS(f"Created doctor: {email} / {password}"))
        else:
            user.email = email
            user.role = User.Role.DOCTOR
            user.full_name = user.full_name or "Dr. Taiba"
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            self.stdout.write(self.style.WARNING(f"Updated doctor: {email} / {password}"))
