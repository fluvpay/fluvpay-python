"""Recurso Withdrawals: saques PIX da conta para uma chave PIX."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import Withdrawal, WithdrawalsPage
from . import BaseResource


class Withdrawals(BaseResource):
    """Saques PIX. Operacao live-only (nao suporta sandbox)."""

    def create(
        self,
        params: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> Withdrawal:
        """Cria um saque PIX (POST /withdrawals/).

        Campos: amount_cents (obrigatorio, 100..10000000), pix_key (obrigatorio),
        pix_key_type (obrigatorio: cpf|cnpj|email|phone|evp), description.

        Live-only: com chave fluv_test_ a API responde 403
        (SANDBOX_NOT_SUPPORTED_FOR_WITHDRAWALS).

        Se ``idempotency_key`` nao for informado, um UUIDv4 e gerado automaticamente.
        """
        key = idempotency_key or self._client.new_idempotency_key()
        body = self._client._clean_body(dict(params))
        data = self._client.request(
            "POST",
            "/withdrawals/",
            body=body,
            idempotency_key=key,
        )
        return Withdrawal.from_dict(data)

    def retrieve(self, withdrawal_id: str) -> Withdrawal:
        """Recupera um saque por ID (GET /withdrawals/{withdrawal_id})."""
        data = self._client.request("GET", f"/withdrawals/{withdrawal_id}")
        return Withdrawal.from_dict(data)

    def list(
        self,
        *,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        status: Optional[str] = None,
    ) -> WithdrawalsPage:
        """Lista saques (GET /withdrawals/).

        Envelope limit/offset/total.
        """
        params = {"limit": limit, "offset": offset, "status": status}
        data = self._client.request("GET", "/withdrawals/", params=params)
        return WithdrawalsPage.from_dict(data)
