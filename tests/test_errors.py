"""Testes de mapeamento de erro (status -> excecao tipada)."""

from __future__ import annotations

import httpx
import pytest
import respx

from fluvpay import (
    FluvPayAuthenticationError,
    FluvPayConflictError,
    FluvPayNotFoundError,
    FluvPayPermissionError,
    FluvPayRateLimitError,
    FluvPayServerError,
    FluvPayValidationError,
)

BASE = "https://api.fluvpay.com/api/v1"


@respx.mock
def test_422_vira_validation_error_com_details(client):
    body = {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Dados invalidos",
            "details": [
                {
                    "field": "amount_cents",
                    "message": "Input should be greater than or equal to 100",
                    "type": "greater_than_equal",
                }
            ],
            "trace_id": "01J123",
        }
    }
    respx.post(f"{BASE}/charges/").mock(return_value=httpx.Response(422, json=body))

    with pytest.raises(FluvPayValidationError) as exc:
        client.charges.create({"amount_cents": 1})

    err = exc.value
    assert err.status_code == 422
    assert err.code == "VALIDATION_ERROR"
    assert err.trace_id == "01J123"
    assert len(err.details) == 1
    assert err.details[0].field == "amount_cents"
    assert err.details[0].type == "greater_than_equal"


@respx.mock
def test_409_vira_conflict_error(client):
    body = {"error": {"code": "IDEMPOTENCY_CONFLICT", "message": "Chave reutilizada"}}
    respx.post(f"{BASE}/charges/").mock(return_value=httpx.Response(409, json=body))

    with pytest.raises(FluvPayConflictError) as exc:
        client.charges.create({"amount_cents": 5000})

    assert exc.value.code == "IDEMPOTENCY_CONFLICT"
    assert exc.value.status_code == 409


@respx.mock
def test_429_vira_rate_limit_error_com_retry_after(client):
    body = {"error": {"code": "RATE_LIMITED", "message": "Devagar"}}
    # max_retries do client e 2; aqui devolvemos 429 sempre para esgotar e lancar.
    respx.get(f"{BASE}/charges/chg_x").mock(
        return_value=httpx.Response(429, json=body, headers={"Retry-After": "7"})
    )

    with pytest.raises(FluvPayRateLimitError) as exc:
        client.charges.retrieve("chg_x")

    assert exc.value.code == "RATE_LIMITED"
    assert exc.value.status_code == 429
    assert exc.value.retry_after == 7.0


@respx.mock
def test_401_403_404_500(client):
    cases = [
        (401, FluvPayAuthenticationError),
        (403, FluvPayPermissionError),
        (404, FluvPayNotFoundError),
        (500, FluvPayServerError),
    ]
    for status, exc_cls in cases:
        body = {"error": {"code": "X", "message": f"erro {status}"}}
        respx.get(f"{BASE}/charges/chg_{status}").mock(
            return_value=httpx.Response(status, json=body)
        )
        with pytest.raises(exc_cls) as exc:
            client.charges.retrieve(f"chg_{status}")
        assert exc.value.status_code == status
