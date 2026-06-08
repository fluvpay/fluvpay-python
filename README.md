# FluvPay Python

SDK oficial da FluvPay para Python. Cobre cobranças PIX, saques, transferências internas e verificação de webhooks, com tipagem forte e erros idiomáticos. A interface é declarativa e estável, adequada tanto a integrações conduzidas por desenvolvedores quanto a agentes e sistemas de IA que consomem a documentação para integrar.

- Requer Python 3.9 ou superior.
- Cliente HTTP construído sobre [httpx](https://www.python-httpx.org/).
- Retentativas automáticas em operações seguras, `Idempotency-Key` gerada automaticamente e erros tipados.

## Instalação

O pacote está publicado no PyPI:

```bash
pip install fluvpay
```

A instalação direta a partir do repositório também é suportada:

```bash
pip install "git+https://github.com/fluvpay/fluvpay-python.git"
```

Uma referência marcada com tag pode ser fixada:

```bash
pip install "git+https://github.com/fluvpay/fluvpay-python.git@v1.0.0"
```

## Início rápido

```python
from fluvpay import FluvPay, FluvPayValidationError, verify_signature

client = FluvPay("fluv_test_sua_chave_de_teste")

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

mesma = client.charges.retrieve(charge.id)
print("Status atual:", mesma.status)

pagina = client.charges.list(page=1, per_page=20, status="paid")
print(f"Página {pagina.page} de {pagina.total} cobranças, há mais? {pagina.has_next}")
for item in pagina:
    print(" -", item.id, item.amount_cents, item.status)


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

Valores monetários são expressos em centavos. A verificação de webhook usa o corpo cru da requisição (bytes), nunca o JSON re-serializado.

## Autenticação

A autenticação usa a API key passada ao construtor. O ambiente é determinado pelo prefixo da chave: `fluv_live_` seleciona produção e `fluv_test_` seleciona o sandbox.

```python
from fluvpay import FluvPay

client = FluvPay("fluv_live_sua_chave_aqui")
```

A base URL padrão é `https://api.fluvpay.com/api/v1` e pode ser sobrescrita com o parâmetro `base_url`.

## Referência de recursos

Cada recurso corresponde a um conjunto de rotas do contrato da API.

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

Withdrawals (saques PIX, disponíveis apenas em produção):

```python
client.withdrawals.create(params, idempotency_key=None)  # POST /withdrawals/
client.withdrawals.list(limit=, offset=, status=)        # GET  /withdrawals/
client.withdrawals.retrieve(withdrawal_id)               # GET  /withdrawals/{id}
```

Internal Transfers (transferências entre contas FluvPay, disponíveis apenas em produção):

```python
client.internal_transfers.create(params, idempotency_key=None)  # POST /internal-transfers/
client.internal_transfers.list(direction=, limit=, offset=)     # GET  /internal-transfers/
client.internal_transfers.retrieve(transfer_id)                 # GET  /internal-transfers/{id}
```

Sandbox (disponível apenas com chave `fluv_test_`):

```python
client.sandbox.reset()       # POST /test/reset
client.sandbox.scenarios()   # GET  /test/scenarios
```

### Criação de cobrança: campos aceitos

`charges.create` aceita exatamente os campos do contrato. Os campos `currency` e `method` não são aceitos e produzem resposta 422.

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

Os estados possíveis de uma cobrança são `pending`, `paid`, `expired`, `cancelled` e `refunded`.

### Paginação

Existem dois envelopes de paginação, expostos como objetos de página tipados, iteráveis e compatíveis com `len()`:

- `charges.list` e `transactions.list` retornam `page`, `per_page`, `total`, `has_next` e `has_prev`.
- `withdrawals.list` e `internal_transfers.list` retornam `limit`, `offset` e `total`.

```python
page = client.withdrawals.list(limit=10, offset=0)
print(page.limit, page.offset, page.total)
for w in page:
    print(w.id, w.status, w.net_cents)
```

## Webhooks

A FluvPay assina cada entrega. O header `X-FluvPay-Signature` carrega o valor `v1=<hex>`, calculado da seguinte forma:

```
hex = HMAC_SHA256(secret, "{timestamp}." + rawBody)
```

`secret` é o valor `whsec_...` exibido na criação do webhook, `timestamp` provém do header `X-FluvPay-Timestamp` e `rawBody` são os bytes crus do corpo. A verificação deve usar o corpo cru, nunca o JSON re-serializado.

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

Os eventos disponíveis são `charge.created`, `charge.paid`, `charge.expired`, `charge.cancelled`, `charge.refunded`, `payout.created`, `payout.completed` e `payout.failed`.

## Erros

Todas as exceções herdam de `FluvPayError` e expõem os atributos `code`, `message`, `details`, `trace_id` e `status_code`. O tipo da exceção é determinado pelo status HTTP da resposta.

| Status | Exceção |
|---|---|
| 400 / 422 | `FluvPayValidationError` |
| 401 | `FluvPayAuthenticationError` |
| 403 | `FluvPayPermissionError` |
| 404 | `FluvPayNotFoundError` |
| 409 | `FluvPayConflictError` |
| 429 | `FluvPayRateLimitError` (atributo `retry_after`) |
| 5xx | `FluvPayServerError` |
| rede / timeout | `FluvPayConnectionError` |

```python
from fluvpay import FluvPayRateLimitError

try:
    client.charges.list()
except FluvPayRateLimitError as err:
    print("Rate limit. Tente novamente em", err.retry_after, "segundos.")
```

## Idempotência

As operações de escrita (`charges.create`, `withdrawals.create`, `internal_transfers.create`) usam o header `Idempotency-Key`. Quando a chave não é informada, o SDK gera um UUIDv4. O reenvio da mesma chave retorna a resposta original. O reuso da mesma chave com um payload diferente resulta em `FluvPayConflictError` com código `IDEMPOTENCY_CONFLICT`.

```python
chave = FluvPay.new_idempotency_key()
client.charges.create({"amount_cents": 5000}, idempotency_key=chave)
```

## Retentativas

O SDK realiza até 2 retentativas por padrão, com backoff exponencial e jitter, restritas a operações seguras: requisições GET e POSTs que carregam `Idempotency-Key`. As retentativas ocorrem apenas em respostas 429, respostas 5xx e falhas de conexão. Em respostas 429, o header `Retry-After` é respeitado.

```python
client = FluvPay("fluv_live_...", max_retries=4)   # aumentar o limite
client = FluvPay("fluv_live_...", max_retries=0)   # desativar
```

## Desenvolvimento

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

Os testes unitários executam sem rede, com o httpx interceptado por respx. O teste de smoke contra o sandbox executa somente quando a variável de ambiente `FLUVPAY_TEST_KEY` (prefixo `fluv_test_`) está presente; na ausência dela, o teste é pulado.

## Licença

MIT.
