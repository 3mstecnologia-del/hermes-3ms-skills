# hermes-3ms-skills

Repositório **público oficial** de skills e MCP servers da **3MS Tecnologia** para o Hermes Agent.

Fonte canônica de distribuição: [github.com/3mstecnologia-del/hermes-3ms-skills](https://github.com/3mstecnologia-del/hermes-3ms-skills).

## Objetivo

Publicar conhecimento operacional de infraestrutura (telecom/ISP) para o Hermes e para a comunidade: auditoria, diagnóstico, configuração segura e troubleshooting — **sem** dados de clientes nem credenciais.

## Estrutura

```
hermes-3ms-skills/
├── AGENTS.md              # Regras para agentes de desenvolvimento
├── SKILLS-CATALOG.md      # Catálogo oficial (versão e status)
├── CONTRIBUTING.md        # Como contribuir
├── SECURITY.md            # Política de segurança
├── .hermes/skills/3mstecnologia/   # Skills oficiais
└── mcp/                   # MCP servers oficiais
```

## Skills disponíveis

| Skill | Versão | Status | Descrição |
|-------|--------|--------|-----------|
| [`olt-intelbras-g08-ops`](.hermes/skills/3mstecnologia/olt-intelbras-g08-ops/SKILL.md) | 0.1.0 | DEV | OLT Intelbras G08 (GPON) |
| [`mikrotik-routeros-ops`](.hermes/skills/3mstecnologia/mikrotik-routeros-ops/SKILL.md) | 0.1.0 | DEV | MikroTik RouterOS 6/7 |

Catálogo completo: [SKILLS-CATALOG.md](SKILLS-CATALOG.md).

## Status das skills

| Status | Significado |
|--------|-------------|
| **DEV** | Em desenvolvimento; não homologada por completo; pode mudar; **não** é configuração universalmente validada |
| **LAB** | Testada em laboratório ou hardware controlado |
| **STABLE** | Suficientemente homologada para uso operacional **dentro do escopo documentado** |
| **DEPRECATED** | Mantida só por compatibilidade ou histórico |

Skills **DEV** podem existir neste repositório público, desde que o status esteja explícito no catálogo e no `CHANGELOG.md` da skill.

A saída real do equipamento e a documentação do fabricante prevalecem sobre exemplos das skills.

## Instalação no Hermes

```bash
git clone https://github.com/3mstecnologia-del/hermes-3ms-skills.git
cd hermes-3ms-skills
mkdir -p ~/.hermes/skills
cp -a .hermes/skills/3mstecnologia ~/.hermes/skills/
```

Depois: `/reload-skills` ou reinicie a sessão. Commits em `main` **não** são deploy automático no Hermes.

## Publicação (fonte canônica)

Este GitHub público é a fonte oficial das skills 3MS. Fluxo:

```
DESENVOLVER → VALIDAR → SECRET SCAN → COMMIT → PUSH → GITHUB
```

Não publicar conteúdo que falhou em validação ou secret scan.

## Contribuição

Ver [CONTRIBUTING.md](CONTRIBUTING.md) e [AGENTS.md](AGENTS.md).

## Segurança

Não envie senhas, tokens, communities SNMP reais, chaves privadas (incluindo WireGuard), backups ou dados de clientes. Use placeholders (`<HOST>`, `<PASSWORD>`, `<SNMP_COMMUNITY>`, `<WG_PRIVATE_KEY>`).

Vulnerabilidades: [SECURITY.md](SECURITY.md).

## Licença

MIT — [LICENSE](LICENSE).
