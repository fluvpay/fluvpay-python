"""Fixtures e helpers compartilhados pelos testes unit (sem rede)."""

from __future__ import annotations

import pytest

from fluvpay import FluvPay

TEST_KEY = "fluv_test_abc123"
BASE_URL = "https://api.fluvpay.com/api/v1"


@pytest.fixture()
def client() -> FluvPay:
    """Cliente apontado para a base URL real, mas com a rede mockada por respx."""
    c = FluvPay(TEST_KEY, base_url=BASE_URL, max_retries=2, backoff_factor=0.0)
    yield c
    c.close()


@pytest.fixture()
def charge_payload() -> dict:
    """Resposta minima valida de uma Charge (campos required do openapi)."""
    return {
        "id": "chg_01J0000000000000000000000",
        "merchant_id": "mer_01J0000000000000000000000",
        "amount_cents": 5000,
        "currency": "BRL",
        "status": "pending",
        "payment_method": "pix",
        "fee_processor_cents": 50,
        "fee_platform_cents": 10,
        "metadata": {},
        "created_at": "2026-06-08T12:00:00Z",
        "updated_at": "2026-06-08T12:00:00Z",
        "pix_copy_paste": "00020126...",
        "pix_qr_code": "data:image/png;base64,AAAA",
    }
