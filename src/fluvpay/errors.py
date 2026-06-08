"""Excecoes tipadas da FluvPay.

Todo erro de API carrega o envelope ``{"error": {code, message, details, trace_id}}``
mapeado para uma excecao especifica conforme o status HTTP. Erros de rede/timeout
viram ``FluvPayConnectionError``. A base comum e ``FluvPayError``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class ErrorDetail:
    """Um item de ``error.details`` (validacao campo a campo)."""

    __slots__ = ("field", "message", "type")

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        type: Optional[str] = None,
    ) -> None:
        self.message = message
        self.field = field
        self.type = type

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "ErrorDetail":
        return cls(
            message=raw.get("message", ""),
            field=raw.get("field"),
            type=raw.get("type"),
        )

    def __repr__(self) -> str:  # pragma: no cover - representacao auxiliar
        return f"ErrorDetail(field={self.field!r}, message={self.message!r}, type={self.type!r})"


class FluvPayError(Exception):
    """Base de todos os erros do SDK.

    Carrega o codigo canonico, a mensagem em PT-BR, os detalhes de validacao,
    o ``trace_id`` para correlacionar nos logs e o status HTTP quando houver.
    """

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[List[ErrorDetail]] = None,
        trace_id: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details: List[ErrorDetail] = details or []
        self.trace_id = trace_id

    def __repr__(self) -> str:  # pragma: no cover - representacao auxiliar
        return (
            f"{type(self).__name__}(code={self.code!r}, status_code={self.status_code!r}, "
            f"message={self.message!r}, trace_id={self.trace_id!r})"
        )


class FluvPayValidationError(FluvPayError):
    """400 / 422: dados invalidos ou estado impeditivo (ex: INSUFFICIENT_BALANCE)."""


class FluvPayAuthenticationError(FluvPayError):
    """401: autenticacao obrigatoria ou chave invalida."""


class FluvPayPermissionError(FluvPayError):
    """403: escopo insuficiente, conta sem permissao ou operacao indisponivel no sandbox."""


class FluvPayNotFoundError(FluvPayError):
    """404: recurso nao encontrado."""


class FluvPayConflictError(FluvPayError):
    """409: conflito (inclui IDEMPOTENCY_CONFLICT)."""


class FluvPayRateLimitError(FluvPayError):
    """429: rate limit excedido. Veja ``retry_after`` (header Retry-After, em segundos)."""

    def __init__(self, message: str, *, retry_after: Optional[float] = None, **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.retry_after = retry_after


class FluvPayServerError(FluvPayError):
    """5xx: erro interno da FluvPay."""


class FluvPayConnectionError(FluvPayError):
    """Falha de rede, DNS ou timeout antes de obter uma resposta HTTP."""


class FluvPaySignatureVerificationError(FluvPayError):
    """A assinatura do webhook nao confere (ou o timestamp esta fora da tolerancia)."""


_STATUS_TO_ERROR = {
    400: FluvPayValidationError,
    401: FluvPayAuthenticationError,
    403: FluvPayPermissionError,
    404: FluvPayNotFoundError,
    409: FluvPayConflictError,
    422: FluvPayValidationError,
    429: FluvPayRateLimitError,
}


def _parse_retry_after(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def error_from_response(
    status_code: int,
    body: Optional[Dict[str, Any]],
    *,
    retry_after_header: Optional[str] = None,
) -> FluvPayError:
    """Constroi a excecao tipada a partir do status e do envelope de erro."""
    envelope = (body or {}).get("error") if isinstance(body, dict) else None
    if isinstance(envelope, dict):
        code = envelope.get("code")
        message = envelope.get("message") or f"Erro HTTP {status_code}"
        raw_details = envelope.get("details") or []
        details = [
            ErrorDetail.from_dict(d) for d in raw_details if isinstance(d, dict)
        ]
        trace_id = envelope.get("trace_id")
    else:
        code = None
        message = f"Erro HTTP {status_code}"
        details = []
        trace_id = None

    if status_code == 429:
        return FluvPayRateLimitError(
            message,
            code=code,
            status_code=status_code,
            details=details,
            trace_id=trace_id,
            retry_after=_parse_retry_after(retry_after_header),
        )

    if status_code >= 500:
        cls: type = FluvPayServerError
    else:
        cls = _STATUS_TO_ERROR.get(status_code, FluvPayError)

    return cls(
        message,
        code=code,
        status_code=status_code,
        details=details,
        trace_id=trace_id,
    )
