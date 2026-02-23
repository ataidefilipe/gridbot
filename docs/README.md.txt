## Especificação do problema (MVP)

### Objetivo

Construir um **grid bot simples em Python** para **Spot**, começando em **BTC/USDT** (mais fácil e líquido) e evoluindo depois para **BTC/ETH**.

### Entradas (runtime)

* `exchange`: `binance` ou `pionex`
* `symbol`: inicialmente `BTC/USDT` (na Binance é BTCUSDT)
* `mode`: `long` ou `short` (**short = inverter a lógica**, sem alavancagem)
* `initial_capital` e `initial_asset` (você escolhe no início):

  * para **long**: normalmente começar em **USDT**
  * para **short (invertido, spot)**: normalmente começar em **BTC**
* `range_pct_bottom` e `range_pct_top` (percentuais relativos ao preço de referência no start)

  * exemplo: `bottom = -10%`, `top = +10%`
* `grid_intervals`: inteiro `N` (você definiu que é **N intervalos**)
* `check_interval_minutes`: inteiro `X`
* `dry_run`: `true/false`

### Decisões já fechadas

* Grid **geométrico**
* Range **fixo no MVP** (documentar evolução para range dinâmico)
* Fora do range: **continua só pro lado válido**
* Ordens **LIMIT**
* Execução por **checagem periódica**
* Se pular vários níveis entre checks: **executa só 1 ordem por ciclo**
* Partial fill: **ignorar e tratar como filled** (na prática: só reagir quando status = CLOSED/FILLED)
* PnL: **simplificado**
* Sem stop, sem caps extras de risco
* Logs simples + salvar estado em arquivo

---

## Definição operacional de LONG e “SHORT invertido” (Spot)

Como você confirmou, a semântica é:

* **LONG**: ganhar quando o preço sobe (ex.: BTC/USDT sobe). Bot tende a **comprar mais baixo e vender um nível acima**.
* **SHORT (invertido em Spot)**: não é short “de verdade” (não vende a descoberto). É um modo que tende a **vender primeiro (se você tiver BTC)** e recomprar mais abaixo, tentando aumentar USDT (ou reduzir exposição a BTC) quando o preço cai.

**Implicação prática:** para o modo *short invertido* fazer sentido em spot, o capital inicial precisa vir **em BTC** (ou o bot precisa converter parte do USDT para BTC no início).

---

## Grid geométrico com range percentual

### 1) Preço de referência no start

No momento `t0`, o bot lê `P0` (last/mark do spot).

### 2) Range absoluto

* `P_bottom = P0 * (1 + range_pct_bottom)`
* `P_top    = P0 * (1 + range_pct_top)`

### 3) N intervalos geométricos

Defina razão:

* `r = (P_top / P_bottom) ** (1 / N)`

Níveis (N+1 níveis para N intervalos):

* `L[i] = P_bottom * r**i`, para `i = 0..N`

---

## Lógica de execução (state machine simples, 1 ordem por tick)

### Estado mínimo salvo em arquivo

* `config`: parâmetros acima + timestamp start
* `grid_levels`: `L[]`
* `last_price`
* `phase`: `"BUY"` ou `"SELL"`
* `active_order`: `{id, side, price, qty, grid_index}`
* `last_filled_grid_index`
* `position`: saldos estimados (simplificados) em base/quote
* `pnl_simplified`: acumulado por operação (ver abaixo)

### Regras gerais

* Sempre manter **no máximo 1 ordem ativa** (para respeitar “executa só 1 por ciclo” e evitar overengineering).
* A cada `X` minutos:

  1. Ler preço atual `P`
  2. Consultar status da `active_order` (se existir)
  3. Se a ordem estiver **FILLED/CLOSED**:

     * atualizar estado
     * alternar `phase` (BUY → SELL ou SELL → BUY)
     * criar a próxima ordem (se existir nível válido)
  4. Se não há ordem ativa:

     * criar a ordem inicial coerente com o modo/phase

### Modo LONG (padrão)

* Start sugerido:

  * `phase = BUY`
  * capital inicial em **USDT**
* Escolha do nível de BUY:

  * encontre o maior `i` tal que `L[i] <= P` (nível “logo abaixo”)
  * próxima compra: `buy_index = i` (ou `i-1`, dependendo da sua preferência de “distância”; MVP: `i`)
* Ao preencher BUY em `L[buy_index]`:

  * próxima SELL em `L[buy_index + 1]` (se `<= P_top`)
* Fora do range:

  * se `P < P_bottom`: só faz BUY no `L[0]` (se houver saldo)
  * se `P > P_top`: só faz SELL no `L[N]` **apenas se** você já estiver segurando BTC por compras anteriores; caso contrário, espera

### Modo SHORT invertido (Spot)

* Start sugerido:

  * `phase = SELL`
  * capital inicial em **BTC**
* Escolha do nível de SELL:

  * encontre o menor `i` tal que `L[i] >= P` (nível “logo acima”)
  * próxima venda: `sell_index = i`
* Ao preencher SELL em `L[sell_index]`:

  * próxima BUY em `L[sell_index - 1]` (se `>= P_bottom`)
* Fora do range:

  * se `P > P_top`: só faz SELL em `L[N]` (se tiver BTC)
  * se `P < P_bottom`: só faz BUY em `L[0]` (se tiver USDT após vendas)

---

## Tamanho de ordem (dividir capital entre grids)

Você decidiu “divide o capital entre os grids” e “tamanho fixo”.

Uma forma simples (MVP) é definir um **notional por trade**:

* `notional_per_grid = initial_notional / N`

Para **LONG** (compras):

* `qty_base = notional_per_grid / order_price`

Para **SHORT invertido** (vendas):

* se capital inicial está em BTC:

  * `qty_base = (initial_btc / N)` (distribui BTC pelos N “slots”)

**Arredondamento obrigatório**

* Ajustar `qty_base` conforme `stepSize/minQty` e `priceTick` do símbolo (exchangeInfo na Binance). Isso evita rejeição por precisão.

---

## Taxas e “grid step mínimo” (para não operar no prejuízo)

* Binance spot (nível base): **0,10% maker / 0,10% taker**. ([Binance][1])
* Pionex spot: **0,05%** (spot). ([Pionex][2])

Como você quer PnL simplificado e decisões simples, use uma regra de sanidade:

* `fee_roundtrip ≈ 2 * fee_rate` (compra + venda)
* exigir que o **ganho do grid** (percentual entre `L[i]` e `L[i+1]`) seja **maior** que `fee_roundtrip` com folga.

Sugestão MVP:

* Binance: grid step **> ~0,30%** (0,20% de fees + folga)
* Pionex: grid step **> ~0,15%** (0,10% + folga)

Se o range e o N gerarem step menor que isso, o bot deve **avisar em log** e continuar (ou abortar — você decide depois).

---

## PnL simplificado (por ciclo buy→sell ou sell→buy)

Para cada “round” completo:

* LONG:

  * `pnl_quote ≈ (sell_price - buy_price) * qty_base - fees_quote_est`
* SHORT invertido:

  * `pnl_quote ≈ (sell_price - buy_price) * qty_base - fees_quote_est`
  * (mesma fórmula, o que muda é a ordem: vende antes, compra depois)

`fees_quote_est` pode ser:

* `fee_rate * (notional_buy + notional_sell)`

---

## Dry-run (obrigatório no MVP)

* Não envia ordens.
* Simula fills de forma conservadora:

  * BUY “enche” se `P <= buy_price`
  * SELL “enche” se `P >= sell_price`
* Atualiza estado e PnL como se tivesse executado.

---

## Persistência e operação

* Script local em loop infinito.
* Estado em `state.json` (atualizar a cada tick e a cada fill).
* Logs: console + arquivo.

---

## Binance vs Pionex (documentação e custos para o MVP)

### Custos (fees)

* **Binance**: spot base 0,10%/0,10%. ([Binance][1])
* **Pionex**: spot 0,05%. ([Pionex][2])

### Rate limit (impacta estabilidade)

* **Binance**: limites e rateLimits são expostos via `exchangeInfo`; há limites por peso e ordens. ([Centro de Desenvolvedores Binance][3])
* **Pionex**: limite geral **10 req/s por IP** e **10 req/s por conta** (private). ([Pionex Doc][4])

### Teste sem dinheiro real

* **Binance Spot Testnet** existe e tem endpoint base documentado. ([Centro de Desenvolvedores Binance][5])
* Para Pionex, na documentação que localizei há endpoints/limites, mas não vi referência clara a um “spot testnet” equivalente (para o MVP, isso pesa).

### API e implementação

* Pionex tem endpoint simples de criar ordem (`POST /api/v1/trade/order`) e consultar ordem. ([Pionex Doc][6])
* Autenticação Pionex usa headers específicos (`PIONEX-KEY`, `PIONEX-SIGNATURE`) e timestamp. ([Pionex Doc][7])

### Recomendação para o seu MVP

**Binance** tende a atender melhor o MVP por:

* ter **Spot Testnet** (validação sem risco),
* documentação ampla e limites bem descritos,
* ecossistema mais comum para bots.

**Pionex** faz sentido se:

* você prioriza reduzir fee (0,05%),
* e aceita testar direto em real/dry-run (sem uma testnet equivalente no fluxo).

---

## Próximos passos (documentação de evolução, sem implementar agora)

1. Evoluir de BTC/USDT para **BTC/ETH** (cross).
2. Permitir **reinvestimento** (compounding) opcional.
3. Permitir **recentralizar range** (range dinâmico) quando preço encostar bordas.
4. Passar de “1 ordem ativa” para “várias ordens em livro” (grid clássico) — só se necessário.

---

## Pontos que ainda ficam como parâmetro (não precisa decidir agora)

* `grid_intervals (N)`: valor inteiro (ex.: 20, 50…)
* `check_interval_minutes (X)`: ex.: 1, 5, 15
* `range_pct_bottom/top`: ex.: -10% / +10%
* `mode`: long vs short invertido
* `initial_asset`: USDT ou BTC

Se você quiser, no próximo passo eu transformo isso em um **README técnico** + **pseudocódigo** do loop e do `state.json` (estrutura exata), já pronto para virar código Python.

[1]: https://www.binance.com/en/fee?utm_source=chatgpt.com "Spot Trading Fee Rate"
[2]: https://www.pionex.com/en/fees?utm_source=chatgpt.com "Pionex Trading Fee | 0.05%"
[3]: https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits?utm_source=chatgpt.com "LIMITS | Binance Open Platform"
[4]: https://pionex-doc.gitbook.io/apidocs/restful/general/rate-limit?utm_source=chatgpt.com "Rate Limit | APIDocs"
[5]: https://developers.binance.com/docs/binance-spot-api-docs/testnet/rest-api/general-api-information?utm_source=chatgpt.com "General API Information | Binance Open Platform"
[6]: https://pionex-doc.gitbook.io/apidocs/restful/orders/new-order?utm_source=chatgpt.com "New Order | APIDocs"
[7]: https://pionex-doc.gitbook.io/apidocs/restful/general/basic?utm_source=chatgpt.com "Basic Info | APIDocs"
