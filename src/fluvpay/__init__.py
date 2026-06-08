"""SDK oficial da FluvPay para Python.

Uso basico:

    from fluvpay import FluvPay

    client = FluvPay("fluv_test_...")
    charge = client.charges.create({"amount_cents": 5000, "description": "Pedido 123"})
    print(charge.id, charge.status, charge.pix_copy_paste)
"""

from __future__ import annotations

__version__ = "1.0.0"

from . import webhooks
from .client import FluvPay, is_test_key
from .errors import (
    ErrorDetail,
    FluvPayAuthenticationError,
    FluvPayConflictError,
    FluvPayConnectionError,
    FluvPayError,
    FluvPayNotFoundError,
    FluvPayPermissionError,
    FluvPayRateLimitError,
    FluvPayServerError,
    FluvPaySignatureVerificationError,
    FluvPayValidationError,
)
from .models import (
    Charge,
    ChargeListItem,
    ChargesPage,
    Customer,
    InternalTransfer,
    InternalTransfersPage,
    SandboxReset,
    SandboxScenarios,
    Transaction,
    TransactionsPage,
    WebhookEvent,
    Withdrawal,
    WithdrawalsPage,
)
from .webhooks import EVENT_TYPES, compute_signature, verify_signature

__all__ = [
    "__version__",
    "FluvPay",
    "is_test_key",
    "webhooks",
    "verify_signature",
    "compute_signature",
    "EVENT_TYPES",
    "WebhookEvent",
    "Charge",
    "ChargeListItem",
    "ChargesPage",
    "Customer",
    "Transaction",
    "TransactionsPage",
    "Withdrawal",
    "WithdrawalsPage",
    "InternalTransfer",
    "InternalTransfersPage",
    "SandboxReset",
    "SandboxScenarios",
    "ErrorDetail",
    "FluvPayError",
    "FluvPayValidationError",
    "FluvPayAuthenticationError",
    "FluvPayPermissionError",
    "FluvPayNotFoundError",
    "FluvPayConflictError",
    "FluvPayRateLimitError",
    "FluvPayServerError",
    "FluvPayConnectionError",
    "FluvPaySignatureVerificationError",
]
