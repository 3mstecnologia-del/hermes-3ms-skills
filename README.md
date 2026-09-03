# Hermes — 3MS Tecnologia

Repositório oficial de **skills** e **MCP servers** para o Hermes Agent (3MS Tecnologia).

A pasta `madalena.3mstecnologia.com` ao lado deste projeto é apenas material de referência/estudo. Este repositório é a fonte versionada do que será usado em produção.

## Estrutura

```
hermes/
├── .hermes/skills/     # Skills do Hermes Agent (SKILL.md por pasta)
│   └── 3mstecnologia/  # Namespace 3MS
└── mcp/                # MCP servers (Python, integrações API, etc.)
```

## Skills disponíveis

| Skill | Descrição |
|-------|-----------|
| [`olt-intelbras-g08-ops`](.hermes/skills/3mstecnologia/olt-intelbras-g08-ops/SKILL.md) | Operação GPON da OLT Intelbras G08 (provisionamento, diagnóstico, SNMP) |

Catálogo completo: [SKILLS-CATALOG.md](SKILLS-CATALOG.md)

## Instalar skills no Hermes

Na máquina onde o Hermes roda:

```bash
mkdir -p ~/.hermes/skills
cp -a .hermes/skills/3mstecnologia ~/.hermes/skills/
```

Depois, no Hermes: `/reload-skills` ou reinicie a sessão.

## Adicionar nova skill

1. Crie uma pasta em `.hermes/skills/3mstecnologia/<nome-da-skill>/`
2. Adicione `SKILL.md` com frontmatter `name` e `description`
3. Opcional: `references/` para documentação detalhada
4. Atualize `SKILLS-CATALOG.md`
5. Commit e push

## Adicionar MCP server

1. Crie uma pasta em `mcp/<nome-do-mcp>/`
2. Inclua `README.md`, `requirements.txt` ou `pyproject.toml`, e `.env.example` (nunca commite `.env`)
3. Documente variáveis e ferramentas expostas

## Verificação

```bash
find .hermes/skills -name 'SKILL.md' -print
```
