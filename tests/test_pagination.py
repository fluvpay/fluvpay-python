"""Testes dos tres envelopes de paginacao distintos."""

from __future__ import annotations

import httpx
import respx

from fluvpay import (
    InternalTransfersPage,
    TransactionsPage,
    WithdrawalsPage,
)

BASE = "https://api.fluvpay.com/api/v1"


@respx.mock
def test_transactions_list_envelope_page_per_page(client):
    body = {
        "data": [
            {
                "id": "tx_1",
                "merchant_id": "mer_1",
                "type": "charge",
                "direction": "credit",
                "amount_cents": 1000,
                "fee_cents": 10,
                "net_amount_cents": 990,
                "status": "completed",
                "metadata": {},
                "created_at": "2026-06-08T12:00:00Z",
            }
        ],
        "page": 1,
        "per_page": 20,
        "total": 1,
        "has_next": False,
        "has_prev": False,
    }
    respx.get(f"{BASE}/transactions/").mock(return_value=httpx.Response(200, json=body))

    page = client.transactions.list(page=1, per_page=20)

    assert isinstance(page, TransactionsPage)
    assert page.page == 1
    assert page.per_page == 20
    assert page.has_next is False
    assert page.data[0].type == "charge"
    assert page.data[0].direction == "credit"


@respx.mock
def test_withdrawals_list_envelope_limit_offset(client):
    body = {
        "data": [
            {
                "id": "wd_1",
                "status": "completed",
                "amount_cents": 5000,
                "fee_cents": 100,
                "net_cents": 4900,
                "pix_key": "user@example.com",
                "pix_key_type": "email",
                "created_at": "2026-06-08T12:00:00Z",
            }
        ],
        "limit": 10,
        "offset": 20,
        "total": 35,
    }
    route = respx.get(f"{BASE}/withdrawals/").mock(
        return_value=httpx.Response(200, json=body)
    )

    page = client.withdrawals.list(limit=10, offset=20, status="completed")

    assert isinstance(page, WithdrawalsPage)
    assert page.limit == 10
    assert page.offset == 20
    assert page.total == 35
    assert page.data[0].net_cents == 4900
    assert page.data[0].pix_key_type == "email"

    sent = route.calls.last.request.url
    assert sent.params["limit"] == "10"
    assert sent.params["offset"] == "20"
    assert sent.params["status"] == "completed"


@respx.mock
def test_internal_transfers_list_envelope_limit_offset(client):
    body = {
        "data": [
            {
                "id": "it_1",
                "from_merchant_id": "mer_a",
                "to_merchant_id": "mer_b",
                "amount_cents": 2500,
                "status": "completed",
                "created_at": "2026-06-08T12:00:00Z",
            }
        ],
        "limit": 20,
        "offset": 0,
        "total": 1,
    }
    route = respx.get(f"{BASE}/internal-transfers/").mock(
        return_value=httpx.Response(200, json=body)
    )

    page = client.internal_transfers.list(direction="sent")

    assert isinstance(page, InternalTransfersPage)
    assert page.limit == 20
    assert page.offset == 0
    assert page.data[0].from_merchant_id == "mer_a"
    assert route.calls.last.request.url.params["direction"] == "sent"
