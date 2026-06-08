"""Smoke no sandbox real, GATED por FLUVPAY_TEST_KEY.

Roda apenas se a env FLUVPAY_TEST_KEY (prefixo fluv_test_) estiver presente; caso
contrario, e pulado. NUNCA faz rede nos testes unit; este modulo e o unico que toca
a internet, e so quando explicitamente habilitado.
"""

from __future__ import annotations

import os

import pytest

from fluvpay import Charge, FluvPay, is_test_key

TEST_KEY = os.environ.get("FLUVPAY_TEST_KEY")

pytestmark = pytest.mark.skipif(
    not TEST_KEY or not TEST_KEY.startswith("fluv_test_"),
    reason="FLUVPAY_TEST_KEY (fluv_test_...) ausente: smoke no sandbox pulado.",
)


@pytest.fixture()
def live_client():
    base_url = os.environ.get("FLUVPAY_BASE_URL", "https://api.fluvpay.com/api/v1")
    c = FluvPay(TEST_KEY, base_url=base_url)
    yield c
    c.close()


def test_chave_e_de_teste():
    assert is_test_key(TEST_KEY)


def test_fluxo_basico_sandbox(live_client):
    # Limpa o sandbox antes de comecar.
    reset = live_client.sandbox.reset()
    assert reset.reset is True

    # Cria uma cobranca.
    charge = live_client.charges.create(
        {"amount_cents": 5000, "description": "Smoke test SDK"}
    )
    assert isinstance(charge, Charge)
    assert charge.amount_cents == 5000
    assert charge.status in {"pending", "paid", "expired", "cancelled", "refunded"}

    # Recupera pela ID.
    fetched = live_client.charges.retrieve(charge.id)
    assert fetched.id == charge.id

    # Lista e confere o envelope page/per_page.
    page = live_client.charges.list(per_page=10)
    assert page.per_page == 10
    assert any(item.id == charge.id for item in page.data)


def test_scenarios_disponivel(live_client):
    scenarios = live_client.sandbox.scenarios()
    assert isinstance(scenarios.scenarios, list)
