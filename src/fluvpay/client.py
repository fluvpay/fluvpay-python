"""Cliente HTTP da FluvPay.

Estilo Stripe: um objeto ``FluvPay`` configurado com a API key, expondo recursos
(``charges``, ``transactions``, ``withdrawals``, ``internal_transfers``, ``sandbox``).
Transporte sobre httpx, com retries (apenas GET e POSTs idempotentes), geracao
automatica de Idempotency-Key (UUIDv4) e mapeamento de erro tipado.
"""

from __future__ import annotations

import random
import time
import uuid
from typing import Any, Dict, Mapping, Optional

import httpx

from . import __version__
from .errors import (
    FluvPayConnectionError,
    FluvPayRateLimitError,
    FluvPayServerError,
    error_from_response,
)

DEFAULT_BASE_URL = "https://api.fluvpay.com/api/v1"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_MAX_BACKOFF = 8.0


def _is_test_key(api_key: str) -> bool:
    return api_key.startswith("fluv_test_")


def is_test_key(api_key: str) -> bool:
    """Retorna True se a chave for de sandbox (prefixo ``fluv_test_``)."""
    return _is_test_key(api_key)


class _Response:
    """Resultado normalizado de uma requisicao (status + JSON ja parseado)."""

    __slots__ = ("status_code", "json", "headers")

    def __init__(self, status_code: int, json: Any, headers: Mapping[str, str]) -> None:
        self.status_code = status_code
        self.json = json
        self.headers = headers


class FluvPay:
    """Cliente principal da FluvPay.

    Args:
        api_key: chave da API (``fluv_live_...`` ou ``fluv_test_...``).
        base_url: URL base (padrao producao/sandbox unificado).
        timeout: timeout por requisicao em segundos.
        max_retries: tentativas extras em 429/5xx/conexao (so GET e POSTs idempotentes).
        backoff_factor: fator do backoff exponencial com jitter.
        http_client: instancia httpx.Client opcional (para reuso/testes).
    """

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        if not api_key or not isinstance(api_key, str):
            raise ValueError("api_key e obrigatoria e deve ser uma string nao vazia.")

        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor

        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)

        # Importacao tardia evita ciclo de import com os modulos de recurso.
        from .resources.charges import Charges
        from .resources.internal_transfers import InternalTransfers
        from .resources.sandbox import Sandbox
        from .resources.transactions import Transactions
        from .resources.withdrawals import Withdrawals

        self.charges = Charges(self)
        self.transactions = Transactions(self)
        self.withdrawals = Withdrawals(self)
        self.internal_transfers = InternalTransfers(self)
        self.sandbox = Sandbox(self)

    # ----------------------------------------------------------------- helpers

    @property
    def is_test_mode(self) -> bool:
        """True se a chave configurada for de sandbox."""
        return _is_test_key(self.api_key)

    def _default_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": f"fluvpay-python/{__version__}",
            "Accept": "application/json",
        }

    @staticmethod
    def _clean_params(params: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not params:
            return None
        return {k: v for k, v in params.items() if v is not None}

    @staticmethod
    def _clean_body(body: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if body is None:
            return None
        return {k: v for k, v in body.items() if v is not None}

    @staticmethod
    def new_idempotency_key() -> str:
        """Gera um Idempotency-Key UUIDv4."""
        return str(uuid.uuid4())

    # ----------------------------------------------------------------- request

    def request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        retry: Optional[bool] = None,
    ) -> Any:
        """Executa uma requisicao e devolve o JSON ja parseado (ou lanca erro tipado)."""
        url = f"{self.base_url}{path}"
        headers = self._default_headers()
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if body is not None:
            headers["Content-Type"] = "application/json"

        upper = method.upper()
        # Retry so para GET e POSTs idempotentes (com Idempotency-Key).
        if retry is None:
            retry = upper == "GET" or (upper == "POST" and idempotency_key is not None)

        max_attempts = (self.max_retries + 1) if retry else 1
        clean_params = self._clean_params(params)

        last_exc: Optional[BaseException] = None
        for attempt in range(max_attempts):
            try:
                http_resp = self._http.request(
                    upper,
                    url,
                    params=clean_params,
                    json=body,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_exc = exc
                if self._should_retry_connection(retry, attempt, max_attempts):
                    self._sleep_backoff(attempt, None)
                    continue
                raise FluvPayConnectionError(
                    f"Timeout ao conectar na FluvPay: {exc}"
                ) from exc
            except httpx.TransportError as exc:
                last_exc = exc
                if self._should_retry_connection(retry, attempt, max_attempts):
                    self._sleep_backoff(attempt, None)
                    continue
                raise FluvPayConnectionError(
                    f"Falha de conexao com a FluvPay: {exc}"
                ) from exc

            resp = self._normalize(http_resp)

            if resp.status_code < 300:
                return resp.json

            # Erro: decide retry para 429/5xx.
            if self._should_retry_status(retry, resp.status_code, attempt, max_attempts):
                retry_after = self._retry_after_seconds(resp)
                self._sleep_backoff(attempt, retry_after)
                continue

            raise error_from_response(
                resp.status_code,
                resp.json if isinstance(resp.json, dict) else None,
                retry_after_header=resp.headers.get("Retry-After"),
            )

        # Esgotou as tentativas em erro de conexao.
        if last_exc is not None:
            raise FluvPayConnectionError(
                f"Falha de conexao com a FluvPay apos {max_attempts} tentativas: {last_exc}"
            ) from last_exc
        raise FluvPayConnectionError("Falha de conexao com a FluvPay.")  # pragma: no cover

    # ----------------------------------------------------------------- internals

    @staticmethod
    def _normalize(http_resp: httpx.Response) -> _Response:
        try:
            parsed = http_resp.json()
        except ValueError:
            parsed = None
        return _Response(http_resp.status_code, parsed, http_resp.headers)

    @staticmethod
    def _should_retry_connection(retry: bool, attempt: int, max_attempts: int) -> bool:
        return retry and attempt < max_attempts - 1

    @staticmethod
    def _should_retry_status(
        retry: bool, status_code: int, attempt: int, max_attempts: int
    ) -> bool:
        if not retry or attempt >= max_attempts - 1:
            return False
        return status_code == 429 or status_code >= 500

    @staticmethod
    def _retry_after_seconds(resp: _Response) -> Optional[float]:
        raw = resp.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _sleep_backoff(self, attempt: int, retry_after: Optional[float]) -> None:
        if retry_after is not None and retry_after >= 0:
            delay = retry_after
        else:
            base = self.backoff_factor * (2 ** attempt)
            jitter = random.uniform(0, self.backoff_factor)
            delay = min(base + jitter, DEFAULT_MAX_BACKOFF)
        if delay > 0:
            time.sleep(delay)

    # ----------------------------------------------------------------- lifecycle

    def close(self) -> None:
        """Fecha o cliente HTTP subjacente (se foi criado pelo SDK)."""
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> "FluvPay":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
