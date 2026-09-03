# Contributing to hermes-3ms-skills

Obrigado por contribuir com skills e MCPs para o ecossistema Hermes (3MS Tecnologia).

## Objetivo do projeto

Este repositório é a fonte oficial de **skills de infraestrutura** e **MCP servers** para o Hermes Agent. O material deve ser útil para operação real (ISP/telecom), seguro por padrão e adequado para compartilhamento com a comunidade.

## Como propor uma nova skill

1. Abra uma issue descrevendo o equipamento/serviço e o escopo operacional.
2. Crie a skill em `.hermes/skills/3mstecnologia/<skill-name>/`.
3. Atualize `SKILLS-CATALOG.md`.
4. Abra um pull request com descrição clara do que foi adicionado ou alterado.

Namespace oficial: **`3mstecnologia`**.

## Estrutura esperada

```
.hermes/skills/3mstecnologia/<skill-name>/
├── SKILL.md          # Obrigatório — conteúdo operacional para o Hermes
├── README.md         # Recomendado — documentação humana
├── CHANGELOG.md      # Recomendado — histórico SemVer
├── references/       # Opcional — CLI, OIDs, procedimentos extensos
├── examples/         # Opcional — cenários anonimizados
└── tests/            # Opcional — cenários de validação
```

Consulte também [AGENTS.md](AGENTS.md).

## Versionamento

Use [Semantic Versioning](https://semver.org/):

- `0.x.x` — desenvolvimento / validação
- `1.0.0+` — estável para distribuição

Status sugeridos: **DEV** → **LAB** → **STABLE** → **DEPRECATED**.

Registre versão e status em `CHANGELOG.md` e `SKILLS-CATALOG.md`.

## Documentação obrigatória

Para skills de hardware ou software de rede, informe quando aplicável:

- fabricante;
- modelo;
- tecnologia (ex.: GPON, EPON);
- firmware validado;
- data ou contexto da última validação.

## Comandos e procedimentos

- Comandos devem ser **documentados** ou **testados** em equipamento/laboratório.
- Diferencie claramente:
  - **confirmado** — validado em ambiente real ou manual oficial verificado;
  - **hipótese** — derivado de documentação sem validação em campo.
- **Não misture** sintaxe entre fabricantes ou plataformas (Huawei, ZTE, Intelbras, VSOL, etc.).
- A saída real do equipamento prevalece sobre exemplos genéricos.

## Exemplos

- Use placeholders: `<HOST>`, `<USERNAME>`, `<PASSWORD>`, `<VLAN_ID>`, `<SNMP_COMMUNITY>`.
- Anonimize clientes, sites, topologias e identificadores reais.
- Não inclua backups, configs exportadas ou dumps de `running-config`.

## Segredos — proibição absoluta

Nunca envie:

- senhas, tokens, API keys;
- communities SNMP reais;
- chaves privadas (`.pem`, `.key`, etc.);
- arquivos `.env` com credenciais;
- credenciais de clientes ou ambientes de produção.

Use apenas `.env.example` com nomes de variáveis, sem valores reais.

## Mudanças destrutivas

Comandos ou procedimentos que possam causar interrupção (reboot, factory reset, erase, delete em massa, firmware upgrade, alteração de uplink/VLAN crítica) devem:

- estar claramente classificados como **destrutivos**;
- exigir confirmação explícita na skill;
- seguir fluxo **read-first**: identificar → inspecionar → diagnosticar → planejar → backup → aplicar → validar → persistir.

## MCP servers

Coloque MCPs em `mcp/<nome>/`.

Política **Docker-first**:

- preferir `Dockerfile` e `compose.yaml`;
- evitar dependências instaladas globalmente no host;
- documentar ferramentas expostas e variáveis em `README.md`;
- incluir `.env.example` (nunca `.env` real).

## Pull requests

Um PR deve:

- ter escopo focado (uma skill ou um MCP por vez, quando possível);
- não introduzir secrets;
- atualizar catálogo e changelog quando relevante;
- descrever o que foi testado e o que permanece em DEV.

Não há pipeline de CI neste momento — revise manualmente antes de abrir o PR.

## Código de conduta

Seja respeitoso, objetivo e técnico. Rejeitamos contribuições que exponham dados de clientes ou que copiem integralmente material de terceiros sem atribuição e licença compatível.
