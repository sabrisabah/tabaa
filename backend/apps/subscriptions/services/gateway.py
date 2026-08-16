from __future__ import annotations

import base64
import json
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from django.conf import settings


@dataclass
class GatewayChargeResult:
    transaction_id: str
    order_id: str
    redirect_url: str
    status: str
    card_brand: str = ""
    card_last4: str = ""
    gateway_token: str = ""
    raw: dict | None = None


def _detect_brand(pan: str) -> str:
    if pan.startswith("4"):
        return "visa"
    if pan.startswith(("51", "52", "53", "54", "55")) or pan.startswith("2"):
        return "mastercard"
    if pan.startswith("9"):
        return "local"
    return "card"


def _mask_last4(pan: str) -> str:
    digits = "".join(ch for ch in pan if ch.isdigit())
    return digits[-4:] if len(digits) >= 4 else "0000"


class PaymentGateway:
    """
    PCI-aware payment gateway adapter.

    Card PAN/CVV must only be forwarded to the processor and never persisted
    by our application. We keep tokens + last4 + brand only.
    """

    def __init__(self) -> None:
        self.mode = getattr(settings, "PAYMENT_GATEWAY_MODE", "sandbox")
        self.frontend_base = getattr(settings, "FRONTEND_BASE_URL", "http://localhost:5173")
        self.api_base = getattr(settings, "BACKEND_PUBLIC_URL", "http://localhost:8000")

    def create_charge(
        self,
        *,
        amount_iqd: int,
        order_id: str,
        customer_phone: str,
        customer_name: str = "",
        saved_token: str | None = None,
        card: dict[str, str] | None = None,
        success_path: str = "/payment/return",
        fail_path: str = "/payment/return",
    ) -> GatewayChargeResult:
        if self.mode == "qicard":
            return self._qicard_create(
                amount_iqd=amount_iqd,
                order_id=order_id,
                customer_phone=customer_phone,
                customer_name=customer_name,
                saved_token=saved_token,
                success_path=success_path,
                fail_path=fail_path,
            )
        return self._sandbox_create(
            amount_iqd=amount_iqd,
            order_id=order_id,
            saved_token=saved_token,
            card=card,
        )

    def _sandbox_create(
        self,
        *,
        amount_iqd: int,
        order_id: str,
        saved_token: str | None,
        card: dict[str, str] | None,
    ) -> GatewayChargeResult:
        """
        Local 3-D Secure simulation.

        Card fields are used only to derive last4/brand/token, then discarded.
        """
        tx_id = f"SANDBOX-{secrets.token_hex(8).upper()}"
        brand = "card"
        last4 = "0000"
        token = saved_token or ""

        if saved_token:
            token = saved_token
            # last4/brand already on SavedPaymentMethod; optional in result
        elif card:
            pan = "".join(ch for ch in str(card.get("number", "")) if ch.isdigit())
            if len(pan) < 13 or len(pan) > 19:
                raise ValueError("Invalid card number.")
            cvv = str(card.get("cvv", "")).strip()
            if not cvv or len(cvv) < 3 or len(cvv) > 4:
                raise ValueError("Invalid CVV.")
            brand = _detect_brand(pan)
            last4 = _mask_last4(pan)
            token = f"tok_{secrets.token_hex(12)}"
            # Explicitly drop sensitive values from local scope usage beyond this point.
            pan = ""
            cvv = ""
            card = None
        else:
            raise ValueError("Provide a saved card token or new card details for the gateway.")

        redirect = (
            f"{self.api_base}/api/payments/card/sandbox-3ds/{order_id}/"
            f"?tx={tx_id}"
        )
        return GatewayChargeResult(
            transaction_id=tx_id,
            order_id=order_id,
            redirect_url=redirect,
            status="awaiting_3ds",
            card_brand=brand,
            card_last4=last4,
            gateway_token=token,
            raw={"mode": "sandbox", "amount_iqd": amount_iqd},
        )

    def _qicard_create(
        self,
        *,
        amount_iqd: int,
        order_id: str,
        customer_phone: str,
        customer_name: str,
        saved_token: str | None,
        success_path: str,
        fail_path: str,
    ) -> GatewayChargeResult:
        """
        Create QiCard / SuperQI hosted checkout (card entered on gateway → 3DS).

        Credentials via env: QICARD_USERNAME, QICARD_PASSWORD, QICARD_TERMINAL_ID,
        QICARD_API_BASE.
        """
        username = getattr(settings, "QICARD_USERNAME", "")
        password = getattr(settings, "QICARD_PASSWORD", "")
        terminal = getattr(settings, "QICARD_TERMINAL_ID", "")
        api_base = getattr(
            settings,
            "QICARD_API_BASE",
            "https://api-gate.qi.iq",
        ).rstrip("/")

        if not (username and password and terminal):
            raise ValueError(
                "QiCard credentials missing. Set QICARD_USERNAME, QICARD_PASSWORD, "
                "QICARD_TERMINAL_ID or use PAYMENT_GATEWAY_MODE=sandbox."
            )

        success_url = f"{self.frontend_base}{success_path}?order={order_id}"
        fail_url = f"{self.frontend_base}{fail_path}?order={order_id}&failed=1"
        notify_url = f"{self.api_base}/api/payments/card/webhook/"

        payload: dict[str, Any] = {
            "amount": amount_iqd,
            "currency": "IQD",
            "orderId": order_id,
            "terminalId": terminal,
            "successUrl": success_url,
            "failureUrl": fail_url,
            "notificationUrl": notify_url,
            "customerInfo": {
                "phone": customer_phone,
                "firstName": (customer_name or "Customer").split(" ")[0],
                "lastName": " ".join((customer_name or "User").split(" ")[1:]) or "User",
            },
        }
        if saved_token:
            payload["token"] = saved_token

        body = json.dumps(payload).encode("utf-8")
        auth = base64.b64encode(f"{username}:{password}".encode()).decode()
        req = urllib.request.Request(
            f"{api_base}/api/v1/payments",
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            raise ValueError(f"QiCard error: {detail}") from exc
        except urllib.error.URLError as exc:
            raise ValueError(f"QiCard unreachable: {exc}") from exc

        redirect = (
            data.get("redirectUrl")
            or data.get("redirect_url")
            or data.get("paymentUrl")
            or ""
        )
        tx_id = str(data.get("transactionId") or data.get("id") or data.get("paymentId") or "")
        if not redirect:
            raise ValueError("QiCard did not return a 3-D Secure redirect URL.")

        return GatewayChargeResult(
            transaction_id=tx_id,
            order_id=order_id,
            redirect_url=redirect,
            status="awaiting_3ds",
            card_brand=str(data.get("cardBrand") or data.get("brand") or ""),
            card_last4=str(data.get("last4") or data.get("cardLast4") or ""),
            gateway_token=str(data.get("token") or saved_token or ""),
            raw={"mode": "qicard", "response_keys": list(data.keys())},
        )

    def verify_webhook_payload(self, data: dict) -> dict:
        """Normalize gateway webhook / callback payload."""
        status_raw = str(
            data.get("status") or data.get("paymentStatus") or data.get("state") or ""
        ).lower()
        paid = status_raw in {"paid", "success", "succeeded", "completed", "captured"}
        return {
            "order_id": str(
                data.get("orderId") or data.get("order_id") or data.get("order") or ""
            ),
            "transaction_id": str(
                data.get("transactionId")
                or data.get("transaction_id")
                or data.get("id")
                or ""
            ),
            "paid": paid,
            "token": str(data.get("token") or data.get("cardToken") or ""),
            "brand": str(data.get("cardBrand") or data.get("brand") or ""),
            "last4": str(data.get("last4") or data.get("cardLast4") or ""),
            "raw": data,
        }
