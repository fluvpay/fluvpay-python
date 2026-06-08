"""Recurso Sandbox: utilitarios de teste (so chave fluv_test_)."""

from __future__ import annotations

from ..models import SandboxReset, SandboxScenarios
from . import BaseResource


class Sandbox(BaseResource):
    """Utilitarios do sandbox. Disponiveis apenas com chave fluv_test_."""

    def reset(self) -> SandboxReset:
        """Apaga todos os dados do sandbox (POST /test/reset)."""
        data = self._client.request("POST", "/test/reset")
        return SandboxReset.from_dict(data)

    def scenarios(self) -> SandboxScenarios:
        """Lista os valores magicos do sandbox (GET /test/scenarios)."""
        data = self._client.request("GET", "/test/scenarios")
        return SandboxScenarios.from_dict(data)
