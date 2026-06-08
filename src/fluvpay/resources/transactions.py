"""Recurso Transactions: extrato financeiro consolidado."""

from __future__ import annotations

from typing import Optional

from ..models import Transaction, TransactionsPage
from . import BaseResource


class Transactions(BaseResource):
    """Lancamentos do extrato (entradas e saidas)."""

    def list(
        self,
        *,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        sort: Optional[str] = None,
    ) -> TransactionsPage:
        """Lista lancamentos (GET /transactions/).

        Envelope page/per_page/total/has_next/has_prev.
        Nao suportado em sandbox: chaves fluv_test_ recebem 403.
        """
        params = {"page": page, "per_page": per_page, "sort": sort}
        data = self._client.request("GET", "/transactions/", params=params)
        return TransactionsPage.from_dict(data)

    def retrieve(self, tx_id: str) -> Transaction:
        """Recupera um lancamento por ID (GET /transactions/{tx_id})."""
        data = self._client.request("GET", f"/transactions/{tx_id}")
        return Transaction.from_dict(data)
