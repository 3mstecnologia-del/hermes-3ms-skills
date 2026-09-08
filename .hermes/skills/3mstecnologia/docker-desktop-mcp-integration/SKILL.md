---
name: docker-desktop-mcp-integration
description: "Use when connecting Hermes to Docker Desktop MCP. Configure an explicit read-only profile through the native Docker gateway."
version: 0.1.0
author: 3MS Tecnologia
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [docker, mcp, docker-desktop, gateway, profiles, security]
---

# Docker Desktop MCP para Hermes

Integração Docker-first sem adapter próprio: Hermes usa seu cliente MCP nativo e inicia o gateway do Docker Desktop por `stdio`.

## Modelo recomendado

- Docker Desktop MCP Toolkit/Gateway gerencia servidores em containers ou endpoints remotos.
- Um profile nomeado é a allowlist de servidores.
- A allowlist de ferramentas do profile deve habilitar somente ferramentas aprovadas.
- Dynamic MCP deve permanecer desabilitado para agentes que precisam de escopo fixo.
- Hermes conecta via `docker mcp gateway run --profile <PROFILE>`; não instale SDK MCP global no Windows.

## Instalação reproduzível

Pré-requisitos: Docker Desktop 4.62+, `docker mcp`, Hermes com cliente MCP nativo.

```bash
docker mcp catalog pull mcp/docker-mcp-catalog:latest
docker mcp profile create --name hermes-docker-readonly
docker mcp profile server add hermes_docker_readonly \
  --server catalog://mcp/docker-mcp-catalog:latest/docker-docs
docker mcp profile tools hermes_docker_readonly \
  --enable docker-docs.fetch_docker_docs
docker mcp feature disable dynamic-tools
hermes mcp add docker_mcp --command docker --connect-timeout 30 \
  --args mcp gateway run --profile hermes_docker_readonly
```

Quando Hermes perguntar se deve habilitar a ferramenta, confirme somente as ferramentas aprovadas.

## Validação

```bash
docker mcp profile show hermes_docker_readonly
docker mcp tools ls --gateway-arg=--profile \
  --gateway-arg=hermes_docker_readonly --format json
hermes mcp list
hermes mcp test docker_mcp
```

A saída esperada para este exemplo é uma única ferramenta read-only: `fetch_docker_docs`.
Teste operacional: peça ao Hermes para usar somente `fetch_docker_docs` e retornar o título do documento.

## Cursor

Conecte o Cursor ao mesmo profile, sem copiar credenciais:

```bash
docker mcp client connect --global --profile hermes_docker_readonly cursor
docker mcp client ls --global
```

O arquivo gerado é específico do usuário e não deve ser commitado. Reinicie o Cursor se a interface ainda não mostrar `MCP_DOCKER`.

## Atualização

- Atualize Docker Desktop pelo canal aprovado pela organização.
- Atualize o catálogo explicitamente (`docker mcp catalog pull ...`).
- Revalide o profile e a lista de ferramentas antes de reconectar clientes.
- Faça upgrade do Hermes pelo procedimento normal e execute `hermes mcp test docker_mcp`.

## Rollback

```bash
hermes mcp remove docker_mcp
docker mcp client disconnect --global cursor
docker mcp profile remove hermes_docker_readonly
```

Remover um profile é destrutivo para a configuração desse profile; exporte-o antes se precisar preservá-lo.

## Troubleshooting

- Sem ferramentas: confirme profile, catálogo, allowlist e `docker mcp tools ls`.
- Gateway indisponível: confirme Docker Desktop ativo; rode `docker mcp gateway run --profile <PROFILE> --dry-run --verbose`.
- Hermes não lista MCP: reinicie a sessão; o cliente descobre MCP no startup.
- Cursor desconectado: `docker mcp client ls --global`, reconecte o profile e reinicie o Cursor.
- Não habilite `dynamic-tools` como correção rápida; isso amplia o conjunto de capacidades além da allowlist.

## Segurança

Nunca publique `config.yaml`, `.env`, tokens, OAuth state, dumps de logs ou perfis contendo infraestrutura privada. Segredos devem permanecer no armazenamento seguro do Docker Desktop ou no ambiente local aprovado.
