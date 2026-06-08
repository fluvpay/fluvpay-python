"""Testes de retry (mock de tempo, sem rede e sem sleep real)."""

from __future__ import annotations

import httpx
import pytest
import respx

from fluvpay import FluvPay, FluvPayValidationError

BASE = "https://api.fluvpay.com/api/v1"


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    """Neutraliza time.sleep no backoff: testes nao podem esperar de verdade."""
    monkeypatch.setattr("fluvpay.client.time.sleep", lambda _s: None)


@respx.mock
def test_retry_429_depois_200_resulta_em_sucesso(client, charge_payload):
    route = respx.get(f"{BASE}/charges/chg_x").mock(
        side_effect=[
            httpx.Response(429, json={"error": {"code": "RATE_LIMITED", "message": "x"}},
                           headers={"Retry-After": "1"}),
            httpx.Response(200, json=charge_payload),
        ]
    )

    charge = client.charges.retrieve("chg_x")

    assert charge.id == charge_payload["id"]
    assert route.call_count == 2


@respx.mock
def test_retry_em_post_com_idempotency_key(client, charge_payload):
    route = respx.post(f"{BASE}/charges/").mock(
        side_effect=[
            httpx.Response(503, json={"error": {"code": "X", "message": "down"}}),
            httpx.Response(201, json=charge_payload),
        ]
    )

    charge = client.charges.create({"amount_cents": 5000})

    assert charge.id == charge_payload["id"]
    assert route.call_count == 2
    # A MESMA Idempotency-Key e reenviada nas tentativas.
    keys = {call.request.headers["Idempotency-Key"] for call in route.calls}
    assert len(keys) == 1


@respx.mock
def test_nao_faz_retry_em_4xx_nao_retentavel(client):
    route = respx.get(f"{BASE}/charges/chg_x").mock(
        return_value=httpx.Response(
            422, json={"error": {"code": "VALIDATION_ERROR", "message": "ruim"}}
        )
    )

    with pytest.raises(FluvPayValidationError):
        client.charges.retrieve("chg_x")

    assert route.call_count == 1  # 422 nao e retentavel


@respx.mock
def test_retry_pode_ser_desligado():
    c = FluvPay("fluv_test_x", base_url=BASE, max_retries=0, backoff_factor=0.0)
    try:
        route = respx.get(f"{BASE}/charges/chg_x").mock(
            return_value=httpx.Response(503, json={"error": {"code": "X", "message": "y"}})
        )
        with pytest.raises(Exception):
            c.charges.retrieve("chg_x")
        assert route.call_count == 1
    finally:
        c.close()
