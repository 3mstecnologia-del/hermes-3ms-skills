# hermes-3ms-skills

Repositório oficial de **skills** e **MCP servers** para o [Hermes Agent](https://github.com/clfigueiredo/hermes-infra-skills), mantido pela **3MS Tecnologia**.

Skills e integrações voltadas a operação de infraestrutura de telecom e ISP: provisionamento, diagnóstico, monitoramento e automação com postura **read-first** e foco em segurança operacional.

## Estrutura

```
hermes-3ms-skills/
├── AGENTS.md              # Regras para agentes de desenvolvimento
├── SKILLS-CATALOG.md      # Catálogo oficial de skills
├── CONTRIBUTING.md        # Como contribuir
├── SECURITY.md            # Política de segurança
├── .hermes/skills/3mstecnologia/   # Skills oficiais (namespace 3MS)
└── mcp/                   # MCP servers oficiais
```

## Skills disponíveis

| Skill | Descrição |
|-------|-----------|
| [`olt-intelbras-g08-ops`](.hermes/skills/3mstecnologia/olt-intelbras-g08-ops/SKILL.md) | Operação GPON da OLT Intelbras G08 |

Catálogo completo: [SKILLS-CATALOG.md](SKILLS-CATALOG.md)

## Instalar skills no Hermes

```bash
git clone https://github.com/3mstecnologia-del/hermes-3ms-skills.git
cd hermes-3ms-skills
mkdir -p ~/.hermes/skills
cp -a .hermes/skills/3mstecnologia ~/.hermes/skills/
```

Depois: `/reload-skills` ou reinicie a sessão do Hermes.

## Adicionar conteúdo

1. **Skill:** `.hermes/skills/3mstecnologia/<nome>/` — ver [AGENTS.md](AGENTS.md) e [CONTRIBUTING.md](CONTRIBUTING.md)
2. **MCP:** `mcp/<nome>/` — Docker-first, `.env.example`, sem secrets
3. Atualizar `SKILLS-CATALOG.md`

## Verificação

```bash
find .hermes/skills -name 'SKILL.md' -print
```

## Licença

MIT — ver [LICENSE](LICENSE).

## Contribuição e segurança

- [CONTRIBUTING.md](CONTRIBUTING.md) — padrões de contribuição
- [SECURITY.md](SECURITY.md) — reporte de vulnerabilidades
