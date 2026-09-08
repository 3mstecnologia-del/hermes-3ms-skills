# Docker Desktop MCP para Hermes

**Status:** DEV (0.1.0)

Integração reutilizável baseada somente em recursos nativos: Docker MCP Toolkit/Gateway + cliente MCP nativo do Hermes. Não há MCP novo nem dependência global adicional.

O profile e a lista de ferramentas são deliberadamente explícitos. O exemplo usa o servidor remoto oficial Docker Docs e habilita apenas `fetch_docker_docs`, uma operação read-only. Substitua o profile e as ferramentas somente após revisão de segurança.

Consulte [`SKILL.md`](SKILL.md) para instalação, conexão com Cursor, atualização, rollback e troubleshooting.

Fontes oficiais:

- https://docs.docker.com/ai/mcp-catalog-and-toolkit/get-started/
- https://docs.docker.com/ai/mcp-catalog-and-toolkit/cli/
- https://docs.docker.com/ai/mcp-catalog-and-toolkit/profiles/
- https://docs.docker.com/ai/mcp-catalog-and-toolkit/mcp-gateway/
- https://hermes-agent.nousresearch.com/docs/
