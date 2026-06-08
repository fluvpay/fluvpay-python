"""Testes mockados de withdrawals, internal_transfers e sandbox (writes + sandbox)."""

from __future__ import annotations

import json

import httpx
import respx

from fluvpay import InternalTransfer, SandboxReset, SandboxScenarios, Withdrawal, is_test_key

BASE = "https://api.fluvpay.com/api/v1"


@respx.mock
def test_withdrawal_create_body_e_idempotency(client):
    payload = {
        "id": "wd_1",
        "status": "pending",
        "amount_cents": 5000,
        "fee_cents": 100,
        "net_cents": 4900,
        "pix_key": "user@example.com",
        "pix_key_type": "email",
        "created_at": "2026-06-08T12:00:00Z",
    }
    route = respx.post(f"{BASE}/withdrawals/").mock(
        return_value=httpx.Response(201, json=payload)
    )

    wd = client.withdrawals.create(
        {
            "amount_cents": 5000,
            "pix_key": "user@example.com",
            "pix_key_type": "email",
        }
    )

    assert isinstance(wd, Withdrawal)
    assert wd.net_cents == 4900
    req = route.calls.last.request
    sent = json.loads(req.content)
    assert sent == {
        "amount_cents": 5000,
        "pix_key": "user@example.com",
        "pix_key_type": "email",
    }
    assert req.headers["Idempotency-Key"]


@respx.mock
def test_internal_transfer_create_body(client):
    payload = {
        "id": "it_1",
        "from_merchant_id": "mer_a",
        "to_merchant_id": "mer_b",
        "amount_cents": 2500,
        "status": "completed",
        "created_at": "2026-06-08T12:00:00Z",
    }
    route = respx.post(f"{BASE}/internal-transfers/").mock(
        return_value=httpx.Response(201, json=payload)
    )

    it = client.internal_transfers.create(
        {"amount_cents": 2500, "recipient_email": "dest@example.com"}
    )

    assert isinstance(it, InternalTransfer)
    assert it.status == "completed"
    sent = json.loads(route.calls.last.request.content)
    assert sent == {"amount_cents": 2500, "recipient_email": "dest@example.com"}


@respx.mock
def test_sandbox_reset_e_scenarios(client):
    respx.post(f"{BASE}/test/reset").mock(
        return_value=httpx.Response(
            200,
            json={"reset": True, "deleted_charges": 3, "merchant_id": "mer_1"},
        )
    )
    respx.get(f"{BASE}/test/scenarios").mock(
        return_value=httpx.Response(
            200,
            json={"info": "valores magicos", "scenarios": [{"amount_cents": 100}]},
        )
    )

    reset = client.sandbox.reset()
    assert isinstance(reset, SandboxReset)
    assert reset.reset is True
    assert reset.deleted_charges == 3

    scenarios = client.sandbox.scenarios()
    assert isinstance(scenarios, SandboxScenarios)
    assert scenarios.info == "valores magicos"
    assert scenarios.scenarios[0]["amount_cents"] == 100


def test_is_test_key_helper():
    assert is_test_key("fluv_test_x") is True
    assert is_test_key("fluv_live_x") is False
