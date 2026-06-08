"""Recursos da API FluvPay (charges, transactions, withdrawals, internal_transfers, sandbox)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..client import FluvPay


class BaseResource:
    """Base comum dos recursos: guarda referencia ao cliente."""

    def __init__(self, client: "FluvPay") -> None:
        self._client = client
