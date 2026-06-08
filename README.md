# FluvPay Python

SDK oficial da FluvPay para Python. Pagamentos PIX, saques, transferências internas e verificação de webhooks, com tipagem forte e tratamento de erros idiomático.

- Python 3.9+
- Cliente HTTP sobre [httpx](https://www.python-httpx.org/)
- Retries automáticos (apenas em operações seguras), Idempotency-Key gerada sozinha, erros tipados

## Instalação

Hoje o SDK se instala direto do código-fonte no GitHub. Use este comando (testado, funciona agora):

```bash
pip install "git+https://github.com/fluvpay/fluvpay-python.git"
```

O comando acima instala a versão da branch principal. Quando uma versão estiver marcada com tag, dá para fixar a referência:

```bash
pip install "git+https://github.com/fluvpay/fluvpay-python.git@v1.0.0"
```

Em breve, quando publicado no PyPI, bastará:

```bash
pip install fluvpay
```

Atenção: `pip install fluvpay` ainda não funciona (o pacote não está no PyPI). Por enquanto, use a instalação a partir do GitHub mostrada acima.

## Autenticação

Use sua API Key no construtor. O modo (produção ou sandbox) vem do prefixo da chave: `fluv_live_` para produção e `fluv_test_` para o sandbox.

```python
from fluvpay import FluvPay

client = FluvPay("fluv_live_sua_chave_aqui")
```

A base URL padrão é `https://api.fluvpay.com/api/v1` e pode ser trocada com `base_url=...`.

## Exemplo completo (copiável)

```python
from fluvpay import FluvPay, FluvPayValidationError, verify_signature

client = FluvPay("fluv_test_sua_chave_de_teste")

# 1. Criar uma cobrança PIX.
#    O valor vai em centavos. A Idempotency-Key é gerada automaticamente.
try:
    charge = client.charges.create(
        {
            "amount_cents": 5000,
            "description": "Pedido 123",
            "customer": {"name": "Maria", "email": "maria@example.com"},
            "metadata": {"pedido_id": "123"},
        }
    )
except FluvPayValidationError as err:
    print("Dados inválidos:", err.code, err.message)
    for d in err.details:
        print(" -", d.field, d.message)
    raise

print("Cobrança criada:", charge.id, charge.status)
print("Copia e cola PIX:", charge.pix_copy_paste)

# 2. Recuperar pela ID.
mesma = client.charges.retrieve(charge.id)
print("Status atual:", mesma.status)

# 3. Listar cobranças (paginação page/per_page).
pagina = client.charges.list(page=1, per_page=20, status="paid")
print(f"Página {pagina.page} de {pagina.total} cobranças, há mais? {pagina.has_next}")
for item in pagina:
    print(" -", item.id, item.amount_cents, item.status)

# 4. Verificar a assinatura de um webhook recebido.
#    Use o corpo CRU da requisição (bytes), nunca o JSON re-serializado.
def handle_webhook(raw_body: bytes, headers: dict):
    event = verify_signature(
        payload=raw_body,
        signature_header=headers["X-FluvPay-Signature"],
        timestamp=headers["X-FluvPay-Timestamp"],
        secret="whsec_seu_segredo_do_webhook",
        event_type=headers.get("X-FluvPay-Event"),
        delivery_id=headers.get("X-FluvPay-Delivery-Id"),
        tolerance_seconds=300,
    )
    if event.type == "charge.paid":
        print("Cobrança paga:", event.data.get("id"))
```

## Recursos e operações

Charges (cobranças PIX):

```python
client.charges.create(params, idempotency_key=None)   # POST /charges/
client.charges.retrieve(charge_id)                    # GET  /charges/{id}
client.charges.list(page=, per_page=, sort=, status=) # GET  /charges/
```

Transactions (extrato):

```python
client.transactions.list(page=, per_page=, sort=)     # GET /transactions/
client.transactions.retrieve(tx_id)                   # GET /transactions/{id}
```

Withdrawals (saques PIX, live-only):

```python
client.withdrawals.create(params, idempotency_key=None)  # POST /withdrawals/
client.withdrawals.list(limit=, offset=, status=)        # GET  /withdrawals/
client.withdrawals.retrieve(withdrawal_id)               # GET  /withdrawals/{id}
```

Internal Transfers (transferências FluvPay para FluvPay, live-only):

```python
client.internal_transfers.create(params, idempotency_key=None)  # POST /internal-transfers/
client.internal_transfers.list(direction=, limit=, offset=)     # GET  /internal-transfers/
client.internal_transfers.retrieve(transfer_id)                 # GET  /internal-transfers/{id}
```

Sandbox (apenas com chave `fluv_test_`):

```python
client.sandbox.reset()       # POST /test/reset
client.sandbox.scenarios()   # GET  /test/scenarios
```

## Criar uma cobrança: campos aceitos

O `charges.create` aceita exatamente os campos do contrato. Não envie `currency` nem `method`: a API rejeita com 422.

| Campo | Tipo | Observação |
|---|---|---|
| `amount_cents` | int, obrigatório | 100 a 100000 (R$ 1,00 a R$ 1.000,00) |
| `description` | str | até 500 caracteres |
| `customer` | dict | `{name?, email?, document?, phone?}` |
| `expires_in_seconds` | int | 60 a 604800 |
| `affiliate_code` | str | 4 a 24 caracteres |
| `split_rule_id` | str | 20 a 32 caracteres |
| `pass_fee_to_payer` | bool | padrão `True` |
| `metadata` | dict | objeto livre |

Status de uma cobrança: `pending`, `paid`, `expired`, `cancelled`, `refunded`.

## Paginação

São três envelopes distintos, expostos como objetos de página tipados (iteráveis, com `len()`):

- `charges.list` e `transactions.list`: `page`, `per_page`, `total`, `has_next`, `has_prev`.
- `withdrawals.list` e `internal_transfers.list`: `limit`, `offset`, `total`.

```python
page = client.withdrawals.list(limit=10, offset=0)
print(page.limit, page.offset, page.total)
for w in page:
    print(w.id, w.status, w.net_cents)
```

## Idempotência

Os POSTs de escrita (`charges.create`, `withdrawals.create`, `internal_transfers.create`) usam o header `Idempotency-Key`. Se você não passar uma, o SDK gera um UUIDv4. Reenviar a mesma chave devolve a resposta original; reusar a chave com um payload diferente resulta em `FluvPayConflictError` (`IDEMPOTENCY_CONFLICT`).

```python
chave = FluvPay.new_idempotency_key()
client.charges.create({"amount_cents": 5000}, idempotency_key=chave)
```

## Erros

Todos os erros herdam de `FluvPayError` e carregam `code`, `message`, `details`, `trace_id` e `status_code`.

| Status | Exceção |
|---|---|
| 400 / 422 | `FluvPayValidationError` |
| 401 | `FluvPayAuthenticationError` |
| 403 | `FluvPayPermissionError` |
| 404 | `FluvPayNotFoundError` |
| 409 | `FluvPayConflictError` |
| 429 | `FluvPayRateLimitError` (campo `retry_after`) |
| 5xx | `FluvPayServerError` |
| rede / timeout | `FluvPayConnectionError` |

```python
from fluvpay import FluvPayRateLimitError

try:
    client.charges.list()
except FluvPayRateLimitError as err:
    print("Rate limit. Tente de novo em", err.retry_after, "segundos.")
```

## Retries

Por padrão o SDK tenta novamente 2 vezes (backoff exponencial com jitter) apenas em operações seguras: GET e POSTs que carregam Idempotency-Key, e somente para 429 e 5xx ou falha de conexão. Em 429 ele respeita o header `Retry-After`.

```python
client = FluvPay("fluv_live_...", max_retries=4)   # ajustar
client = FluvPay("fluv_live_...", max_retries=0)   # desligar
```

## Webhooks

A FluvPay assina cada entrega. O header `X-FluvPay-Signature` traz `v1=<hex>`, onde:

```
hex = HMAC_SHA256(secret, "{timestamp}." + rawBody)
```

`secret` é o `whsec_...` exibido na criação do webhook, `timestamp` vem de `X-FluvPay-Timestamp` e `rawBody` são os bytes crus do corpo. Use sempre o corpo cru, nunca o JSON re-serializado.

```python
from fluvpay import verify_signature, FluvPaySignatureVerificationError

try:
    event = verify_signature(
        payload=raw_body,
        signature_header=request.headers["X-FluvPay-Signature"],
        timestamp=request.headers["X-FluvPay-Timestamp"],
        secret="whsec_...",
        tolerance_seconds=300,
    )
except FluvPaySignatureVerificationError:
    return "assinatura inválida", 400
```

Eventos disponíveis: `charge.created`, `charge.paid`, `charge.expired`, `charge.cancelled`, `charge.refunded`, `payout.created`, `payout.completed`, `payout.failed`.

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Os testes unit rodam sem rede (httpx mockado com respx). O smoke no sandbox roda somente se a env `FLUVPAY_TEST_KEY` (prefixo `fluv_test_`) estiver presente; caso contrário, é pulado.

## Licença

MIT.
