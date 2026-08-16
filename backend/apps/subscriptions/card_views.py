from __future__ import annotations

import secrets

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from django.http import HttpResponse

from apps.subscriptions.models import (
    AdminAlert,
    CardPayment,
    SavedPaymentMethod,
    Subscription,
)
from apps.subscriptions.services.gateway import PaymentGateway


FORBIDDEN_CARD_STORAGE_FIELDS = {
    "card_number",
    "number",
    "pan",
    "cvv",
    "cvc",
    "security_code",
    "full_pan",
}


class SavedPaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedPaymentMethod
        fields = (
            "id",
            "brand",
            "last4",
            "exp_month",
            "exp_year",
            "cardholder_name",
            "is_default",
            "created_at",
        )
        read_only_fields = fields


class CardPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardPayment
        fields = (
            "id",
            "amount_iqd",
            "currency",
            "status",
            "gateway",
            "gateway_transaction_id",
            "gateway_order_id",
            "redirect_url",
            "card_brand",
            "card_last4",
            "failure_reason",
            "paid_at",
            "created_at",
        )
        read_only_fields = fields


class CreateCardPaymentSerializer(serializers.Serializer):
    amount_iqd = serializers.IntegerField(min_value=1000, max_value=5_000_000)
    subscription_id = serializers.IntegerField(required=False)
    saved_method_id = serializers.IntegerField(required=False)
    save_card = serializers.BooleanField(required=False, default=False)
    # Transient card fields — never persisted by our models.
    card_number = serializers.CharField(required=False, write_only=True, max_length=19)
    card_exp_month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    card_exp_year = serializers.IntegerField(required=False, min_value=2024, max_value=2100)
    card_cvv = serializers.CharField(required=False, write_only=True, max_length=4)
    cardholder_name = serializers.CharField(required=False, allow_blank=True, max_length=120)

    def validate(self, attrs):
        from django.conf import settings

        mode = getattr(settings, "PAYMENT_GATEWAY_MODE", "sandbox")
        has_saved = bool(attrs.get("saved_method_id"))
        has_new = bool(attrs.get("card_number"))
        # QiCard hosted checkout: card is typed on the bank/gateway page (best PCI posture).
        if mode == "qicard" and not has_saved and not has_new:
            return attrs
        if not has_saved and not has_new:
            raise serializers.ValidationError(
                "اختر بطاقة محفوظة أو أدخل بطاقة جديدة للدفع عبر البوابة."
            )
        if has_new:
            if not attrs.get("card_cvv"):
                raise serializers.ValidationError({"card_cvv": "CVV مطلوب للإرسال للبوابة فقط."})
            if not attrs.get("card_exp_month") or not attrs.get("card_exp_year"):
                raise serializers.ValidationError("تاريخ انتهاء البطاقة مطلوب.")
        return attrs


def _apply_successful_payment(payment: CardPayment, *, token: str = "", brand: str = "", last4: str = "") -> None:
    payment.status = CardPayment.Status.SUCCEEDED
    payment.paid_at = timezone.now()
    if brand:
        payment.card_brand = brand
    if last4:
        payment.card_last4 = last4
    payment.save(
        update_fields=[
            "status",
            "paid_at",
            "card_brand",
            "card_last4",
            "updated_at",
        ]
    )

    if token and last4:
        method, _ = SavedPaymentMethod.objects.update_or_create(
            user=payment.user,
            gateway_token=token,
            defaults={
                "gateway": payment.gateway,
                "brand": brand or payment.card_brand or "card",
                "last4": last4 or payment.card_last4,
                "cardholder_name": "",
            },
        )
        payment.saved_method = method
        payment.save(update_fields=["saved_method", "updated_at"])

    subscription = payment.subscription
    if subscription and subscription.status in {
        Subscription.Status.PENDING_PAYMENT,
        Subscription.Status.PAID_PENDING_ACTIVATION,
        Subscription.Status.EXPIRED,
    }:
        subscription.mark_paid(
            transaction_id=payment.gateway_transaction_id,
            note="Paid via card gateway (3-D Secure).",
        )
        AdminAlert.objects.create(
            user=payment.user,
            subscription=subscription,
            kind=AdminAlert.Kind.PAYMENT_CONFIRMED,
            title=f"دفع بطاقة ناجح: {payment.gateway_transaction_id}",
            body=(
                f"الهاتف: {payment.user.username}\n"
                f"المبلغ: {payment.amount_iqd} د.ع\n"
                f"رقم العملية: {payment.gateway_transaction_id}\n"
                f"البطاقة: {(payment.card_brand or 'card')} •••• {payment.card_last4}\n"
                "يرجى تفعيل الاشتراك للسماح بعرض الوجبات."
            ),
        )


class SavedPaymentMethodListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        methods = SavedPaymentMethod.objects.filter(user=request.user)
        return Response(SavedPaymentMethodSerializer(methods, many=True).data)

    def delete(self, request: Request) -> Response:
        method_id = request.data.get("id") or request.query_params.get("id")
        method = get_object_or_404(SavedPaymentMethod, id=method_id, user=request.user)
        method.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CreateCardPaymentView(APIView):
    """
    Start a card payment.

    Sensitive card fields are write-only and forwarded to the gateway only.
    Our DB stores token / last4 / transaction id — never PAN or CVV.
    """

    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = CreateCardPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        subscription = None
        if data.get("subscription_id"):
            subscription = get_object_or_404(
                Subscription,
                id=data["subscription_id"],
                user=request.user,
            )
        else:
            subscription = (
                Subscription.objects.filter(
                    user=request.user,
                    status__in={
                        Subscription.Status.PENDING_PAYMENT,
                        Subscription.Status.PAID_PENDING_ACTIVATION,
                        Subscription.Status.EXPIRED,
                    },
                )
                .order_by("-created_at")
                .first()
            )

        saved_method = None
        saved_token = None
        if data.get("saved_method_id"):
            saved_method = get_object_or_404(
                SavedPaymentMethod,
                id=data["saved_method_id"],
                user=request.user,
            )
            saved_token = saved_method.gateway_token

        card_payload = None
        if data.get("card_number"):
            card_payload = {
                "number": data["card_number"],
                "cvv": data["card_cvv"],
                "exp_month": str(data["card_exp_month"]),
                "exp_year": str(data["card_exp_year"]),
                "name": data.get("cardholder_name") or "",
            }

        order_id = f"NTC-{secrets.token_hex(6).upper()}"
        gateway = PaymentGateway()
        try:
            result = gateway.create_charge(
                amount_iqd=data["amount_iqd"],
                order_id=order_id,
                customer_phone=request.user.username,
                customer_name=data.get("cardholder_name") or "",
                saved_token=saved_token,
                card=card_payload,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        finally:
            # Drop sensitive payload from memory as soon as gateway returns.
            card_payload = None

        payment = CardPayment.objects.create(
            user=request.user,
            subscription=subscription,
            saved_method=saved_method,
            amount_iqd=data["amount_iqd"],
            status=CardPayment.Status.AWAITING_3DS,
            gateway=gateway.mode,
            gateway_transaction_id=result.transaction_id,
            gateway_order_id=result.order_id,
            redirect_url=result.redirect_url,
            card_brand=result.card_brand or (saved_method.brand if saved_method else ""),
            card_last4=result.card_last4 or (saved_method.last4 if saved_method else ""),
            raw_gateway_status={
                "status": result.status,
                # Never include PAN/CVV — only non-sensitive keys.
                "mode": gateway.mode,
                "has_token": bool(result.gateway_token),
            },
        )

        # Stash token temporarily on raw status for sandbox completion (not PAN).
        if result.gateway_token and data.get("save_card", True):
            payment.raw_gateway_status["pending_token"] = result.gateway_token
            payment.save(update_fields=["raw_gateway_status", "updated_at"])

        return Response(
            {
                "payment": CardPaymentSerializer(payment).data,
                "three_ds_required": True,
                "redirect_url": result.redirect_url,
                "pci_note": (
                    "Card PAN/CVV are not stored. Only gateway token, last4, "
                    "and transaction id are kept after authentication."
                ),
            },
            status=status.HTTP_201_CREATED,
        )


class CardPaymentStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, order_id: str) -> Response:
        payment = get_object_or_404(CardPayment, gateway_order_id=order_id, user=request.user)
        return Response(CardPaymentSerializer(payment).data)


class CardPaymentWebhookView(APIView):
    """Gateway notification after 3-D Secure / OTP success or failure."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request: Request) -> Response:
        data = request.data if isinstance(request.data, dict) else {}
        normalized = PaymentGateway().verify_webhook_payload(data)
        order_id = normalized["order_id"]
        if not order_id:
            return Response({"detail": "Missing order id."}, status=status.HTTP_400_BAD_REQUEST)

        payment = CardPayment.objects.filter(gateway_order_id=order_id).select_related(
            "subscription", "user"
        ).first()
        if not payment:
            return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

        payment.raw_gateway_status = {
            **(payment.raw_gateway_status or {}),
            "webhook": {k: normalized[k] for k in ("order_id", "transaction_id", "paid", "brand", "last4")},
        }
        if normalized["transaction_id"]:
            payment.gateway_transaction_id = normalized["transaction_id"]

        if normalized["paid"]:
            _apply_successful_payment(
                payment,
                token=normalized["token"] or payment.raw_gateway_status.get("pending_token", ""),
                brand=normalized["brand"] or payment.card_brand,
                last4=normalized["last4"] or payment.card_last4,
            )
        else:
            payment.status = CardPayment.Status.FAILED
            payment.failure_reason = str(data.get("message") or data.get("error") or "Payment failed")
            payment.save(update_fields=["status", "failure_reason", "raw_gateway_status", "gateway_transaction_id", "updated_at"])

        return Response({"ok": True, "status": payment.status})


class Sandbox3DSView(APIView):
    """
    Simulated bank OTP / 3-D Secure page for local development.
    Production uses the real QiCard hosted page instead.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request: Request, order_id: str) -> HttpResponse:
        payment = get_object_or_404(CardPayment, gateway_order_id=order_id)
        tx = request.query_params.get("tx", payment.gateway_transaction_id)
        html = f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>3-D Secure · مصادقة البنك</title>
  <style>
    body {{ font-family: Tahoma, sans-serif; background:#0f172a; color:#e2e8f0; display:flex; min-height:100vh; align-items:center; justify-content:center; margin:0; }}
    .card {{ background:#1e293b; padding:28px; border-radius:16px; width:min(420px, 92vw); box-shadow:0 10px 40px rgba(0,0,0,.35); }}
    h1 {{ font-size:1.15rem; margin:0 0 8px; }}
    p {{ color:#94a3b8; font-size:.9rem; line-height:1.6; }}
    input {{ width:100%; padding:12px; border-radius:10px; border:1px solid #334155; background:#0f172a; color:#fff; font-size:1.2rem; letter-spacing:.3em; text-align:center; box-sizing:border-box; }}
    button {{ width:100%; margin-top:12px; padding:12px; border:0; border-radius:10px; background:#10b981; color:#fff; font-weight:700; cursor:pointer; }}
    .meta {{ font-size:.75rem; color:#64748b; margin-top:14px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>مصادقة 3-D Secure / OTP</h1>
    <p>أدخل رمز التحقق المرسل من البنك لتأكيد دفع
      <strong>{payment.amount_iqd:,}</strong> د.ع
      (•••• {payment.card_last4 or '****'}).</p>
    <form method="post">
      <input name="otp" inputmode="numeric" maxlength="6" placeholder="OTP" required value="123456"/>
      <button type="submit">تأكيد الدفع</button>
    </form>
    <p class="meta">رقم العملية: {tx}<br/>للتجربة استخدم 123456 — في الإنتاج تتم المصادقة على صفحة البنك.</p>
  </div>
</body>
</html>"""
        return HttpResponse(html)

    def post(self, request: Request, order_id: str) -> HttpResponse:
        payment = get_object_or_404(CardPayment, gateway_order_id=order_id)
        otp = (request.data.get("otp") if hasattr(request, "data") else None) or request.POST.get("otp", "")
        frontend = PaymentGateway().frontend_base
        if str(otp).strip() != "123456":
            payment.status = CardPayment.Status.FAILED
            payment.failure_reason = "OTP rejected"
            payment.save(update_fields=["status", "failure_reason", "updated_at"])
            return HttpResponse(
                f'<meta http-equiv="refresh" content="0;url={frontend}/?payment=failed&order={order_id}"/>'
                "OTP failed",
                status=400,
            )

        token = (payment.raw_gateway_status or {}).get("pending_token", "")
        _apply_successful_payment(
            payment,
            token=token,
            brand=payment.card_brand,
            last4=payment.card_last4,
        )
        return HttpResponse(
            f'<meta http-equiv="refresh" content="0;url={frontend}/?payment=success&order={order_id}"/>'
            "Payment approved"
        )
