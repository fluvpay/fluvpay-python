"""Testes do recurso Charges (mockado, sem rede)."""

from __future__ import annotations

import json

import httpx
import respx

from fluvpay import Charge, ChargesPage

BASE = "https://api.fluvpay.com/api/v1"


@respx.mock
def test_create_envia_body_e_headers_corretos(client, charge_payload):
    route = respx.post(f"{BASE}/charges/").mock(
        return_value=httpx.Response(201, json=charge_payload)
    )

    charge = client.charges.create(
        {"amount_cents": 5000, "description": "Pedido 123"}
    )

    assert isinstance(charge, Charge)
    assert charge.id == charge_payload["id"]
    assert charge.status == "pending"
    assert charge.pix_copy_paste == "00020126..."

    request = route.calls.last.request
    sent_body = json.loads(request.content)
    # Body fiel ao contrato: sem currency, sem method.
    assert sent_body == {"amount_cents": 5000, "description": "Pedido 123"}
    assert "currency" not in sent_body
    assert "method" not in sent_body

    # Authorization Bearer + User-Agent + Idempotency-Key auto-gerado.
    assert request.headers["Authorization"] == "Bearer fluv_test_abc123"
    assert request.headers["User-Agent"].startswith("fluvpay-python/")
    assert request.headers["Idempotency-Key"]
    assert len(request.headers["Idempotency-Key"]) == 36  # UUIDv4


@respx.mock
def test_create_respeita_idempotency_key_fornecida(client, charge_payload):
    route = respx.post(f"{BASE}/charges/").mock(
        return_value=httpx.Response(201, json=charge_payload)
    )

    client.charges.create(
        {"amount_cents": 5000}, idempotency_key="minha-chave-fixa"
    )

    assert route.calls.last.request.headers["Idempotency-Key"] == "minha-chave-fixa"


@respx.mock
def test_retrieve_parseia_charge(client, charge_payload):
    respx.get(f"{BASE}/charges/{charge_payload['id']}").mock(
        return_value=httpx.Response(200, json=charge_payload)
    )

    charge = client.charges.retrieve(charge_payload["id"])

    assert charge.id == charge_payload["id"]
    assert charge.fee_platform_cents == 10


@respx.mock
def test_list_parseia_envelope_page_per_page(client):
    body = {
        "data": [
            {
                "id": "chg_1",
                "amount_cents": 1000,
                "currency": "BRL",
                "status": "paid",
                "created_at": "2026-06-08T12:00:00Z",
            }
        ],
        "page": 2,
        "per_page": 20,
        "total": 41,
        "has_next": True,
        "has_prev": True,
    }
    route = respx.get(f"{BASE}/charges/").mock(
        return_value=httpx.Response(200, json=body)
    )

    page = client.charges.list(page=2, per_page=20, status="paid")

    assert isinstance(page, ChargesPage)
    assert page.page == 2
    assert page.per_page == 20
    assert page.total == 41
    assert page.has_next is True
    assert page.has_prev is True
    assert len(page) == 1
    assert page.data[0].status == "paid"

    # Iteravel direto.
    ids = [item.id for item in page]
    assert ids == ["chg_1"]

    # Query string montada corretamente (params None sao omitidos).
    sent = route.calls.last.request.url
    assert sent.params["page"] == "2"
    assert sent.params["per_page"] == "20"
    assert sent.params["status"] == "paid"
    assert "sort" not in sent.params
