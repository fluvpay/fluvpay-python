"""Verificacao de assinatura de webhooks da FluvPay.

A FluvPay assina cada entrega com HMAC-SHA256 sobre ``"{timestamp}." + rawBody``,
usando o segredo ``whsec_...`` do webhook. O header ``X-FluvPay-Signature`` traz
``v1=<hex>``. A verificacao usa comparacao em tempo constante e exige o corpo CRU
(bytes/string como recebidos), nao reserializado.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Optional, Union

from .errors import FluvPaySignatureVerificationError
from .models import WebhookEvent

EVENT_HEADER = "X-FluvPay-Event"
TIMESTAMP_HEADER = "X-FluvPay-Timestamp"
DELIVERY_ID_HEADER = "X-FluvPay-Delivery-Id"
SIGNATURE_HEADER = "X-FluvPay-Signature"

EVENT_TYPES = (
    "charge.created",
    "charge.paid",
    "charge.expired",
    "charge.cancelled",
    "charge.refunded",
    "payout.created",
    "payout.completed",
    "payout.failed",
)


def _to_bytes(value: Union[str, bytes]) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError("payload deve ser str ou bytes")


def compute_signature(secret: Union[str, bytes], timestamp: str, raw_body: Union[str, bytes]) -> str:
    """Recalcula o hex da assinatura: HMAC_SHA256(secret, timestamp + '.' + rawBody)."""
    secret_bytes = _to_bytes(secret)
    signed_payload = _to_bytes(timestamp) + b"." + _to_bytes(raw_body)
    return hmac.new(secret_bytes, signed_payload, hashlib.sha256).hexdigest()


def _extract_v1(signature_header: str) -> Optional[str]:
    """Extrai o hex apos ``v1=`` (aceita multiplos esquemas separados por virgula)."""
    if not signature_header:
        return None
    for part in signature_header.split(","):
        item = part.strip()
        if item.startswith("v1="):
            return item[len("v1=") :].strip()
    return None


def verify_signature(
    payload: Union[str, bytes],
    signature_header: str,
    timestamp: str,
    secret: Union[str, bytes],
    *,
    tolerance_seconds: Optional[int] = None,
    event_type: Optional[str] = None,
    delivery_id: Optional[str] = None,
) -> WebhookEvent:
    """Verifica a assinatura e devolve o evento parseado.

    Args:
        payload: corpo CRU da requisicao (str ou bytes), exatamente como recebido.
        signature_header: valor de ``X-FluvPay-Signature`` (formato ``v1=<hex>``).
        timestamp: valor de ``X-FluvPay-Timestamp``.
        secret: segredo do webhook (``whsec_...``).
        tolerance_seconds: se informado e o timestamp for numerico, rejeita entregas
            mais antigas que esse limite (protecao contra replay).
        event_type: opcional, valor de ``X-FluvPay-Event`` (preenche WebhookEvent.type).
        delivery_id: opcional, valor de ``X-FluvPay-Delivery-Id``.

    Returns:
        WebhookEvent parseado.

    Raises:
        FluvPaySignatureVerificationError: assinatura ausente, invalida ou fora da
        tolerancia de tempo.
    """
    provided = _extract_v1(signature_header or "")
    if not provided:
        raise FluvPaySignatureVerificationError(
            "Assinatura ausente ou em formato invalido (esperado 'v1=<hex>')."
        )

    if tolerance_seconds is not None:
        try:
            ts_int = int(timestamp)
        except (TypeError, ValueError):
            raise FluvPaySignatureVerificationError(
                "Timestamp nao numerico: impossivel validar a tolerancia de tempo."
            )
        age = abs(int(time.time()) - ts_int)
        if age > tolerance_seconds:
            raise FluvPaySignatureVerificationError(
                f"Timestamp fora da tolerancia ({age}s > {tolerance_seconds}s); possivel replay."
            )

    expected = compute_signature(secret, timestamp, payload)
    if not hmac.compare_digest(expected, provided):
        raise FluvPaySignatureVerificationError("Assinatura do webhook nao confere.")

    raw_text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
    try:
        parsed = json.loads(raw_text)
    except (ValueError, TypeError):
        parsed = {}

    resolved_type = event_type or (parsed.get("event") if isinstance(parsed, dict) else None)
    if isinstance(parsed, dict):
        data = parsed.get("data") if isinstance(parsed.get("data"), dict) else parsed
    else:
        data = {}

    return WebhookEvent(
        type=resolved_type,
        delivery_id=delivery_id,
        timestamp=timestamp,
        data=data,
        raw=parsed if isinstance(parsed, dict) else {},
    )
