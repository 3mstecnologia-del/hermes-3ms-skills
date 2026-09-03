# AGENTS.md — hermes-3ms-skills

Instruções para agentes de desenvolvimento que trabalham neste repositório.

## Propósito

Fonte oficial de **skills** e **MCP servers** do Hermes Agent (3MS Tecnologia), com qualidade suficiente para uso interno e compartilhamento futuro com a comunidade.

Repositório GitHub pretendido: **`3mstecnologia-del/hermes-3ms-skills`**. Validar autenticação (`gh auth status`) antes de qualquer operação remota. Não presumir que o remoto já existe ou está configurado.

## Estrutura

```
.hermes/skills/3mstecnologia/<skill-name>/   # Skills Hermes (namespace 3MS)
mcp/<mcp-name>/                               # MCP servers
SKILLS-CATALOG.md                             # Catálogo oficial
```

## Nova skill

Criar em `.hermes/skills/3mstecnologia/<skill-name>/`:

| Arquivo | Obrigatório | Função |
|---------|-------------|--------|
| `SKILL.md` | Sim | Conteúdo operacional para o Hermes (frontmatter `name`, `description`) |
| `README.md` | Recomendado | Documentação humana: objetivo, equipamentos, limitações, fontes |
| `CHANGELOG.md` | Recomendado | Histórico SemVer |
| `references/` | Opcional | CLI, OIDs, procedimentos extensos |
| `examples/` | Opcional | Casos anonimizados |
| `tests/` | Opcional | Cenários de validação |

Atualizar `SKILLS-CATALOG.md` com: nome, versão, status, fabricante, produto, tecnologia, firmware validado, descrição, última validação.

## Novo MCP

- Pasta em `mcp/<nome>/`
- `README.md`, `.env.example` (nunca `.env` real)
- Preferir **Docker** (`Dockerfile`, `compose.yaml`) em vez de dependências no host
- Documentar ferramentas expostas e variáveis de ambiente

## Versionamento

Semantic Versioning. Status: **DEV** → **LAB** → **STABLE** → **DEPRECATED**.

- `0.x.x` — desenvolvimento / validação
- `1.0.0+` — estável para distribuição

## Compatibilidade de hardware

Documentar fabricante, modelo, tecnologia, firmware e status de teste. Não assumir CLI intercambiável entre fabricantes ou entre EPON/GPON. A saída real do equipamento prevalece sobre exemplos genéricos.

## Segurança operacional (skills de infra)

Fluxo padrão **read-first**:

```
Identificar → Inspecionar → Diagnosticar → Planejar → Backup
→ Aplicar (menor mudança) → Validar → Persistir → Reportar
```

Exigir confirmação explícita antes de recomendar: reboot, factory reset, erase, delete em massa, firmware upgrade, alterações de uplink/VLAN/routing/firewall ou exclusão de ONU em escala.

## Conteúdo proibido no repositório

- Credenciais, tokens, communities SNMP, senhas reais
- IPs privados de clientes, topologias identificáveis, dados contratuais
- Trechos extensos de manuais com copyright
- Cópias integrais de skills de terceiros apresentadas como originais 3MS

Use placeholders: `<HOST>`, `<USERNAME>`, `<PASSWORD>`, `<SNMP_COMMUNITY>`, `<API_KEY>`.

## Filosofia de conteúdo

A skill descreve **como operar o produto**; o ambiente fornece **onde e com quais credenciais**.

Errado: "Conecte na OLT 10.x.x.x do cliente X com usuário admin."

Correto: "Conecte na OLT usando `<HOST>` e credenciais do ambiente."

## Distribuição futura (Hermes)

GitHub será a fonte oficial. Fluxo alvo (não implementar auto-update agora):

```
desenvolvimento → validação → commit → release estável
→ Hermes detecta → valida → backup → instala → verifica → rollback se necessário
```

Commits em `main` não devem ser tratados como deploy automático em produção.

## Git — restrições

Sem autorização explícita, não executar: `git push`, criação de repo remoto, `git push --force`, `git reset --hard`, `git clean -fd`, alteração destrutiva de histórico.

Antes de commit: `git status`, revisar secrets, confirmar que apenas arquivos do repo oficial foram alterados.

## Instalação no Hermes (referência)

```bash
mkdir -p ~/.hermes/skills
cp -a .hermes/skills/3mstecnologia ~/.hermes/skills/
# /reload-skills ou reiniciar sessão
```
