"""Modelos de resposta da FluvPay.

Dataclasses tipadas, sem dependencia de runtime (pydantic-free). Cada modelo
carrega ``raw`` com o dict cru recebido, garantindo compatibilidade futura caso a
API adicione campos novos. Os tres envelopes de paginacao distintos sao expostos
como classes separadas (``ChargesPage``/``TransactionsPage`` com page/per_page e
``WithdrawalsPage``/``InternalTransfersPage`` com limit/offset).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Customer:
    """Dados do pagador associados a uma cobranca."""

    name: Optional[str] = None
    email: Optional[str] = None
    document: Optional[str] = None
    phone: Optional[str] = None

    @classmethod
    def from_dict(cls, raw: Optional[Dict[str, Any]]) -> Optional["Customer"]:
        if raw is None:
            return None
        return cls(
            name=raw.get("name"),
            email=raw.get("email"),
            document=raw.get("document"),
            phone=raw.get("phone"),
        )


@dataclass
class Charge:
    """Cobranca PIX (resposta de create/retrieve).

    status: pending | paid | expired | cancelled | refunded.
    """

    id: str
    merchant_id: str
    amount_cents: int
    currency: str
    status: str
    payment_method: str
    fee_processor_cents: int
    fee_platform_cents: int
    created_at: str
    updated_at: str
    description: Optional[str] = None
    customer: Optional[Customer] = None
    expires_at: Optional[str] = None
    paid_at: Optional[str] = None
    pix_qr_code: Optional[str] = None
    pix_copy_paste: Optional[str] = None
    net_amount_cents: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Charge":
        return cls(
            id=raw["id"],
            merchant_id=raw["merchant_id"],
            amount_cents=raw["amount_cents"],
            currency=raw["currency"],
            status=raw["status"],
            payment_method=raw["payment_method"],
            fee_processor_cents=raw["fee_processor_cents"],
            fee_platform_cents=raw["fee_platform_cents"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
            description=raw.get("description"),
            customer=Customer.from_dict(raw.get("customer")),
            expires_at=raw.get("expires_at"),
            paid_at=raw.get("paid_at"),
            pix_qr_code=raw.get("pix_qr_code"),
            pix_copy_paste=raw.get("pix_copy_paste"),
            net_amount_cents=raw.get("net_amount_cents"),
            metadata=raw.get("metadata") or {},
            raw=raw,
        )


@dataclass
class ChargeListItem:
    """Versao enxuta de cobranca usada em listagens."""

    id: str
    amount_cents: int
    currency: str
    status: str
    created_at: str
    description: Optional[str] = None
    paid_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ChargeListItem":
        return cls(
            id=raw["id"],
            amount_cents=raw["amount_cents"],
            currency=raw["currency"],
            status=raw["status"],
            created_at=raw["created_at"],
            description=raw.get("description"),
            paid_at=raw.get("paid_at"),
            raw=raw,
        )


@dataclass
class Transaction:
    """Linha do extrato financeiro consolidado."""

    id: str
    merchant_id: str
    type: str
    direction: str
    amount_cents: int
    fee_cents: int
    net_amount_cents: int
    status: str
    created_at: str
    charge_id: Optional[str] = None
    description: Optional[str] = None
    counterparty_name: Optional[str] = None
    counterparty_document_masked: Optional[str] = None
    counterparty_pix_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Transaction":
        return cls(
            id=raw["id"],
            merchant_id=raw["merchant_id"],
            type=raw["type"],
            direction=raw["direction"],
            amount_cents=raw["amount_cents"],
            fee_cents=raw["fee_cents"],
            net_amount_cents=raw["net_amount_cents"],
            status=raw["status"],
            created_at=raw["created_at"],
            charge_id=raw.get("charge_id"),
            description=raw.get("description"),
            counterparty_name=raw.get("counterparty_name"),
            counterparty_document_masked=raw.get("counterparty_document_masked"),
            counterparty_pix_key=raw.get("counterparty_pix_key"),
            metadata=raw.get("metadata") or {},
            raw=raw,
        )


@dataclass
class Withdrawal:
    """Solicitacao de saque PIX.

    status: pending | processing | completed | failed.
    """

    id: str
    status: str
    amount_cents: int
    fee_cents: int
    net_cents: int
    pix_key: str
    pix_key_type: str
    created_at: str
    description: Optional[str] = None
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "Withdrawal":
        return cls(
            id=raw["id"],
            status=raw["status"],
            amount_cents=raw["amount_cents"],
            fee_cents=raw["fee_cents"],
            net_cents=raw["net_cents"],
            pix_key=raw["pix_key"],
            pix_key_type=raw["pix_key_type"],
            created_at=raw["created_at"],
            description=raw.get("description"),
            completed_at=raw.get("completed_at"),
            failure_reason=raw.get("failure_reason"),
            metadata=raw.get("metadata") or {},
            raw=raw,
        )


@dataclass
class InternalTransfer:
    """Transferencia interna FluvPay para FluvPay.

    status: completed | failed | reversed.
    """

    id: str
    from_merchant_id: str
    to_merchant_id: str
    amount_cents: int
    status: str
    created_at: str
    to_merchant_name: Optional[str] = None
    description: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "InternalTransfer":
        return cls(
            id=raw["id"],
            from_merchant_id=raw["from_merchant_id"],
            to_merchant_id=raw["to_merchant_id"],
            amount_cents=raw["amount_cents"],
            status=raw["status"],
            created_at=raw["created_at"],
            to_merchant_name=raw.get("to_merchant_name"),
            description=raw.get("description"),
            raw=raw,
        )


@dataclass
class SandboxReset:
    """Resultado de ``sandbox.reset()``."""

    reset: bool
    deleted_charges: int
    merchant_id: str
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SandboxReset":
        return cls(
            reset=raw["reset"],
            deleted_charges=raw["deleted_charges"],
            merchant_id=raw["merchant_id"],
            raw=raw,
        )


@dataclass
class SandboxScenarios:
    """Catalogo de valores magicos do sandbox."""

    info: str
    scenarios: List[Dict[str, Any]]
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "SandboxScenarios":
        return cls(
            info=raw["info"],
            scenarios=list(raw.get("scenarios") or []),
            raw=raw,
        )


@dataclass
class ChargesPage:
    """Pagina de cobrancas. Envelope page/per_page/has_next/has_prev."""

    data: List[ChargeListItem]
    page: int
    per_page: int
    total: int
    has_next: bool
    has_prev: bool
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ChargesPage":
        return cls(
            data=[ChargeListItem.from_dict(item) for item in raw.get("data", [])],
            page=raw["page"],
            per_page=raw["per_page"],
            total=raw["total"],
            has_next=raw["has_next"],
            has_prev=raw["has_prev"],
            raw=raw,
        )

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


@dataclass
class TransactionsPage:
    """Pagina do extrato. Envelope page/per_page/has_next/has_prev."""

    data: List[Transaction]
    page: int
    per_page: int
    total: int
    has_next: bool
    has_prev: bool
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "TransactionsPage":
        return cls(
            data=[Transaction.from_dict(item) for item in raw.get("data", [])],
            page=raw["page"],
            per_page=raw["per_page"],
            total=raw["total"],
            has_next=raw["has_next"],
            has_prev=raw["has_prev"],
            raw=raw,
        )

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


@dataclass
class WithdrawalsPage:
    """Pagina de saques. Envelope limit/offset/total."""

    data: List[Withdrawal]
    limit: int
    offset: int
    total: int
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "WithdrawalsPage":
        return cls(
            data=[Withdrawal.from_dict(item) for item in raw.get("data", [])],
            limit=raw["limit"],
            offset=raw["offset"],
            total=raw["total"],
            raw=raw,
        )

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


@dataclass
class InternalTransfersPage:
    """Pagina de transferencias internas. Envelope limit/offset/total."""

    data: List[InternalTransfer]
    limit: int
    offset: int
    total: int
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "InternalTransfersPage":
        return cls(
            data=[InternalTransfer.from_dict(item) for item in raw.get("data", [])],
            limit=raw["limit"],
            offset=raw["offset"],
            total=raw["total"],
            raw=raw,
        )

    def __iter__(self):
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


@dataclass
class WebhookEvent:
    """Evento de webhook ja verificado e parseado.

    type e um dos 8 eventos: charge.created, charge.paid, charge.expired,
    charge.cancelled, charge.refunded, payout.created, payout.completed,
    payout.failed.
    """

    type: Optional[str]
    delivery_id: Optional[str]
    timestamp: Optional[str]
    data: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict, repr=False)
