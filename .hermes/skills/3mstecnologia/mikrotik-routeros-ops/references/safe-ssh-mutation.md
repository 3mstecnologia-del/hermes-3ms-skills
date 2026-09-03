# RouterOS SSH — mutação atômica e evidência

Contrato obrigatório para operações **mutáveis** via SSH não interativo (RouterOS 6 e 7).

Consumidores: esta skill, `network-device-cli-capture` (evidência/transporte) e qualquer automação futura de frota. Não depende de um tenant, site ou equipamento.

Especificação executável: [../tests/safe_routeros_exec.py](../tests/safe_routeros_exec.py).

## Princípio

```
MUTAÇÃO → CAPTURA DE EVIDÊNCIA → LEITURA INDEPENDENTE → VALIDAÇÃO DO ESTADO → PRÓXIMA MUTAÇÃO
```

> Operações mutáveis RouterOS devem ser atômicas, preservar evidência e validar estado depois de cada mutação.

## Proibido

1. Agregar várias mutações independentes num único comando/sessão SSH e tratar o retorno agregado como “tudo ou nada”.
2. Assumir que `exit status != 0` prova que nada foi aplicado.
3. Assumir que `exit status == 0` sozinho prova o estado desejado.
4. Continuar a sequência sem leitura autoritativa pós-mudança.
5. Rollback cego (incluindo `/system reset-configuration`) sem reconciliar o estado real.
6. Tratar ausência de um campo em `print` compacto como ausência da configuração.

## Padrão seguro (`safe_routeros_exec`)

Para **cada** mutação (`add` / `set` / `remove` / `enable` / `disable` / `move`):

1. Ler o pré-estado mínimo autoritativo (consulta específica ou `get`, não um dump amplo).
2. Calcular o diff **fora** do RouterOS. Se o pré-estado já satisfaz a identidade, **não criar de novo** (retry idempotente).
3. Executar **exatamente uma** mutação por fronteira de evidência (preferir uma sessão SSH por mutação).
4. Preservar, por operação:
   - `correlation_id` (mesmo fluxo) e `order` (1, 2, 3…);
   - `started_at` / `finished_at`;
   - representação **sanitizada** do comando;
   - `transport_ok` (SSH/TCP) **independente** do erro de CLI;
   - `exit_status`;
   - `stdout`;
   - `stderr`.
5. Ler o pós-estado autoritativo e comparar com o estado esperado.
6. **Parar** antes da próxima mutação se o resultado não for `applied` confirmado.

## Modelo de resultado

| Resultado | Significado | Próxima mutação | Rollback |
|-----------|-------------|-----------------|----------|
| `applied` | Pós-estado confere; transporte e CLI sem falha | Permitida | Não |
| `not-applied` | Leitura autoritativa confirma que a alteração **não** está presente | Bloqueada | Não (nada a desfazer) |
| `failed-after-apply` | Execução falhou (exit ≠ 0, CLI error ou transporte) **mas** o pós-estado confere | Bloqueada | Não cego — o objeto existe |
| `mismatch` | Pós-estado diverge do esperado | Bloqueada | Só do objeto **confirmado** |
| `indeterminate` | Falta exit/stdout/stderr/transporte, ou leitura inconclusiva | Bloqueada | **Proibido** até reconciliar |

`PASS` operacional exige `applied`. Qualquer outro resultado **não** é PASS.

## Validação: compacto vs determinístico

`print` compacto frequentemente omite atributos (ex.: `comment`). Omissão ≠ ausência.

| Leitura primária (compacta) | Leitura secundária (`get` / `print where` / projeção) | Classificação |
|-----------------------------|------------------------------------------------------|---------------|
| Campo crítico omitido | Campo presente com valor esperado | `applied` (não rollback) |
| Campo omitido ou ausente | Campo ausente | `not-applied` / falha de validação |
| Ordem/formatação muda | Valor da propriedade correto | sem divergência falsa |
| Campo omitido | Secundária indisponível | `indeterminate` / `inconclusive` — parar |

Toda propriedade crítica deve ter uma consulta determinística documentada, por exemplo:

```rsc
:put [/interface wireguard get [find name=<WG_IFACE>] name]
:put [/interface wireguard get [find name=<WG_IFACE>] listen-port]
:put [/interface wireguard get [find name=<WG_IFACE>] comment]
:put [/ip address get [find interface=<WG_IFACE>] address]
:put [/interface wireguard peers get [find interface=<WG_IFACE> public-key="<REMOTE_PUBLIC_KEY>"] allowed-address]
```

Não usar `print detail` na **interface** WireGuard (expõe `private-key`). Não usar `export show-sensitive`. Projetar só as propriedades necessárias.

## Evidência e redação

Persistir apenas projeção mínima. Antes de log/relatório, redigir:

- `password`, `secret`, `token`, `community`
- `private-key`, `preshared-key`, `psk`
- qualquer literal que pareça chave/community

Placeholders em exemplos públicos: `<PASSWORD>`, `<WG_PRIVATE_KEY>`, `<SNMP_COMMUNITY>`.

## Captura de evidência (SSH)

O transporte deve devolver os quatro campos. Se a sessão cair sem `exit status`, o resultado é `indeterminate`.

A skill [`network-device-cli-capture`](../../network-device-cli-capture/SKILL.md) cobre captura prompt-aware e preservação de stdout/stderr. **Mutação** continua nesta skill: capture não aplica `set`/`add`.

Exemplo de fronteira (uma mutação):

```bash
ssh -p <SSH_PORT> <USERNAME>@<HOST> \
  '/interface wireguard add name=<WG_IFACE> listen-port=<WG_PORT> comment="lab"'
echo "exit:$?"
```

Depois, **outra** sessão/comando só de leitura:

```bash
ssh -p <SSH_PORT> <USERNAME>@<HOST> \
  ':put [/interface wireguard get [find name=<WG_IFACE>] comment]'
```

Não encadear o próximo `add`/`set` no mesmo bloco até essa leitura confirmar.

## Rollback

Rollback = comandos inversos **do objeto reconciliado** (ex.: `remove [find name=<WG_IFACE>]` se a interface existe).

Não executar rollback quando o resultado for `indeterminate` ou quando a compacta omitiu um campo que a secundária ainda não confirmou.
