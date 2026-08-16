from django.urls import path

from apps.subscriptions.card_views import (
    CardPaymentStatusView,
    CardPaymentWebhookView,
    CreateCardPaymentView,
    Sandbox3DSView,
    SavedPaymentMethodListView,
)
from apps.subscriptions.views import (
    ConfirmTransferView,
    MySubscriptionView,
    PlanListView,
    SubscribeView,
    SuperQiWebhookView,
)

urlpatterns = [
    path("subscriptions/plans/", PlanListView.as_view(), name="subscription-plans"),
    path("subscriptions/me/", MySubscriptionView.as_view(), name="subscription-me"),
    path("subscriptions/subscribe/", SubscribeView.as_view(), name="subscription-subscribe"),
    path(
        "subscriptions/confirm-transfer/",
        ConfirmTransferView.as_view(),
        name="subscription-confirm-transfer",
    ),
    path(
        "payments/superqi/webhook/",
        SuperQiWebhookView.as_view(),
        name="superqi-webhook",
    ),
    path(
        "payments/card/methods/",
        SavedPaymentMethodListView.as_view(),
        name="card-methods",
    ),
    path(
        "payments/card/create/",
        CreateCardPaymentView.as_view(),
        name="card-create",
    ),
    path(
        "payments/card/status/<str:order_id>/",
        CardPaymentStatusView.as_view(),
        name="card-status",
    ),
    path(
        "payments/card/webhook/",
        CardPaymentWebhookView.as_view(),
        name="card-webhook",
    ),
    path(
        "payments/card/sandbox-3ds/<str:order_id>/",
        Sandbox3DSView.as_view(),
        name="card-sandbox-3ds",
    ),
]
