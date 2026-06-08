"""Recurso Internal Transfers: transferencias entre contas FluvPay."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import InternalTransfer, InternalTransfersPage
from . import BaseResource


class InternalTransfers(BaseResource):
    """Transferencias internas FluvPay para FluvPay. Operacao live-only."""

    def create(
        self,
        params: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> InternalTransfer:
        """Cria uma transferencia interna (POST /internal-transfers/).

        Campos: amount_cents (obrigatorio, 100..10000000), e exatamente um entre
        recipient_email e recipient_merchant_id (ULID de 26 chars), description.

        Live-only: com chave fluv_test_ a API responde 403
        (SANDBOX_NOT_SUPPORTED_FOR_TRANSFERS).

        Se ``idempotency_key`` nao for informado, um UUIDv4 e gerado automaticamente.
        """
        key = idempotency_key or self._client.new_idempotency_key()
        body = self._client._clean_body(dict(params))
        data = self._client.request(
            "POST",
            "/internal-transfers/",
            body=body,
            idempotency_key=key,
        )
        return InternalTransfer.from_dict(data)

    def retrieve(self, transfer_id: str) -> InternalTransfer:
        """Recupera uma transferencia por ID (GET /internal-transfers/{transfer_id})."""
        data = self._client.request("GET", f"/internal-transfers/{transfer_id}")
        return InternalTransfer.from_dict(data)

    def list(
        self,
        *,
        direction: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> InternalTransfersPage:
        """Lista transferencias internas (GET /internal-transfers/).

        ``direction``: sent (enviadas) ou received (recebidas). Default sent.
        Envelope limit/offset/total.
        """
        params = {"direction": direction, "limit": limit, "offset": offset}
        data = self._client.request("GET", "/internal-transfers/", params=params)
        return InternalTransfersPage.from_dict(data)
