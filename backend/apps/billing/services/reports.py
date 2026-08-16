from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.billing.models import Invoice, InvoiceLine, PaymentStatus


def _parse_range(date_from: str | None, date_to: str | None):
    start = parse_date(date_from) if date_from else None
    end = parse_date(date_to) if date_to else None
    return start, end


def revenue_summary(*, date_from: str | None = None, date_to: str | None = None) -> dict:
    qs = Invoice.objects.exclude(
        payment_status__in=[PaymentStatus.CANCELLED, PaymentStatus.REFUNDED],
    )
    start, end = _parse_range(date_from, date_to)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    paid = qs.filter(payment_status__in=[PaymentStatus.PAID, PaymentStatus.PARTIAL])
    totals = paid.aggregate(
        revenue=Sum("amount_paid_iqd"),
        due=Sum("total_due_iqd"),
        discounts=Sum("discount_amount_iqd"),
        count=Count("id"),
    )
    by_method = list(
        paid.values("payment_method")
        .annotate(total=Sum("amount_paid_iqd"), count=Count("id"))
        .order_by("-total"),
    )
    by_status = list(
        qs.values("payment_status").annotate(count=Count("id"), total=Sum("total_due_iqd")),
    )
    by_service = list(
        InvoiceLine.objects.filter(invoice__in=paid)
        .values("service_name_snapshot")
        .annotate(count=Count("id"), revenue=Sum("line_total_iqd"))
        .order_by("-revenue")[:50],
    )
    by_day = list(
        paid.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(revenue=Sum("amount_paid_iqd"), count=Count("id"))
        .order_by("day"),
    )
    mounjaro = list(
        InvoiceLine.objects.filter(
            invoice__in=paid,
            service__code="mounjaro",
        )
        .values("variant_label_snapshot")
        .annotate(count=Sum("quantity"), revenue=Sum("line_total_iqd"))
        .order_by("variant_label_snapshot"),
    )
    discounts = list(
        paid.exclude(discount_amount_iqd=0)
        .values("discount_reason")
        .annotate(count=Count("id"), total=Sum("discount_amount_iqd"))
        .order_by("-total"),
    )

    return {
        "currency": "IQD",
        "date_from": date_from,
        "date_to": date_to,
        "generated_at": timezone.now().isoformat(),
        "totals": {
            "revenue_iqd": int(totals["revenue"] or 0),
            "due_iqd": int(totals["due"] or 0),
            "discounts_iqd": int(totals["discounts"] or 0),
            "invoice_count": int(totals["count"] or 0),
        },
        "by_payment_method": by_method,
        "by_status": by_status,
        "by_service": by_service,
        "by_day": [
            {
                "day": row["day"].isoformat() if row["day"] else None,
                "revenue": int(row["revenue"] or 0),
                "count": row["count"],
            }
            for row in by_day
        ],
        "mounjaro_by_dose": mounjaro,
        "discounts_by_reason": discounts,
    }
