"""Vetor deterministico de assinatura de webhook (sem rede)."""

from __future__ import annotations

import hashlib
import hmac

import pytest

from fluvpay import (
    FluvPaySignatureVerificationError,
    compute_signature,
    verify_signature,
)

# Vetor fixo, pre-computado e conferido contra o algoritmo do brief:
#   hex = HMAC_SHA256(secret, timestamp + "." + rawBody).hexdigest()
SECRET = "whsec_test_secret_123"
TIMESTAMP = "1718000000"
RAW_BODY = (
    '{"event":"charge.paid","data":'
    '{"id":"chg_01J0000000000000000000000","status":"paid"}}'
)
EXPECTED_HEX = "83edd830417f9adac0df5e6f10f4069465a867da6b859ff4de15bb8d6cb52a29"
SIGNATURE_HEADER = f"v1={EXPECTED_HEX}"


def test_vetor_bate_com_algoritmo_independente():
    # Recalcula com hmac puro: prova que o vetor nao foi inventado.
    manual = hmac.new(
        SECRET.encode("utf-8"),
        (TIMESTAMP + "." + RAW_BODY).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    assert manual == EXPECTED_HEX
    assert compute_signature(SECRET, TIMESTAMP, RAW_BODY) == EXPECTED_HEX


def test_verify_signature_retorna_evento():
    event = verify_signature(
        RAW_BODY,
        SIGNATURE_HEADER,
        TIMESTAMP,
        SECRET,
        event_type="charge.paid",
        delivery_id="dlv_1",
    )
    assert event.type == "charge.paid"
    assert event.delivery_id == "dlv_1"
    assert event.timestamp == TIMESTAMP
    assert event.data["id"] == "chg_01J0000000000000000000000"
    assert event.data["status"] == "paid"


def test_verify_signature_aceita_bytes():
    event = verify_signature(
        RAW_BODY.encode("utf-8"), SIGNATURE_HEADER, TIMESTAMP, SECRET
    )
    # type sai do corpo quando event_type nao e passado.
    assert event.type == "charge.paid"


def test_assinatura_adulterada_lanca():
    adulterada = "v1=" + ("0" * 64)
    with pytest.raises(FluvPaySignatureVerificationError):
        verify_signature(RAW_BODY, adulterada, TIMESTAMP, SECRET)


def test_corpo_modificado_lanca():
    with pytest.raises(FluvPaySignatureVerificationError):
        verify_signature(RAW_BODY + " ", SIGNATURE_HEADER, TIMESTAMP, SECRET)


def test_header_sem_v1_lanca():
    with pytest.raises(FluvPaySignatureVerificationError):
        verify_signature(RAW_BODY, EXPECTED_HEX, TIMESTAMP, SECRET)


def test_tolerancia_de_tempo_rejeita_antigo():
    with pytest.raises(FluvPaySignatureVerificationError):
        verify_signature(
            RAW_BODY,
            SIGNATURE_HEADER,
            TIMESTAMP,
            SECRET,
            tolerance_seconds=300,
        )
