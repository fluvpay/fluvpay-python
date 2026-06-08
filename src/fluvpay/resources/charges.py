"""Recurso Charges: criar, recuperar e listar cobrancas PIX."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..models import Charge, ChargesPage
from . import BaseResource


class Charges(BaseResource):
    """Cobrancas PIX."""

    def create(
        self,
        params: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> Charge:
        """Cria uma cobranca PIX (POST /charges/).

        O contrato NAO aceita ``currency`` nem ``method`` (a API rejeita com 422).
        Campos aceitos: amount_cents (obrigatorio, 100..100000), description,
        customer, expires_in_seconds, affiliate_code, split_rule_id,
        pass_fee_to_payer, metadata.

        Se ``idempotency_key`` nao for informado, um UUIDv4 e gerado automaticamente.
        """
        key = idempotency_key or self._client.new_idempotency_key()
        body = self._client._clean_body(dict(params))
        data = self._client.request(
            "POST",
            "/charges/",
            body=body,
            idempotency_key=key,
        )
        return Charge.from_dict(data)

    def retrieve(self, charge_id: str) -> Charge:
        """Recupera uma cobranca por ID (GET /charges/{charge_id})."""
        data = self._client.request("GET", f"/charges/{charge_id}")
        return Charge.from_dict(data)

    def list(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        sort: Optional[str] = None,
        status: Optional[str] = None,
    ) -> ChargesPage:
        """Lista cobrancas (GET /charges/).

        Envelope page/per_page/total/has_next/has_prev.
        """
        params = {
            "page": page,
            "per_page": per_page,
            "sort": sort,
            "status": status,
        }
        data = self._client.request("GET", "/charges/", params=params)
        return ChargesPage.from_dict(data)
