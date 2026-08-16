from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.subscriptions.services.lifecycle import process_subscription_lifecycle


class Command(BaseCommand):
    help = (
        "Send WhatsApp + system alerts before expiry, then expire ended subscriptions "
        "and revoke meal access until renew + admin approval."
    )

    def handle(self, *args, **options):
        result = process_subscription_lifecycle()
        self.stdout.write(
            self.style.SUCCESS(
                f"Warned {result['warned']} · Expired {result['expired']}"
            )
        )
