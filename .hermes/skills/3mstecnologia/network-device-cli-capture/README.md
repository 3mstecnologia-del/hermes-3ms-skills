# network-device-cli-capture

Procedimento reutilizável para capturar configurações de CLIs de rede legadas com SSH restrito, prompts interativos e paginação.

## Escopo

- descoberta e captura read-only;
- host key pinning;
- negociação SSH mínima por dispositivo;
- detecção de prompt/pager;
- artefato bruto somente local e documentação sanitizada.

## Status

`DEV` — versão **1.1.0**. Conteúdo generalizado; valide o comportamento no fabricante e firmware alvo.

Captura continua **somente leitura**. Mutações RouterOS: skill `mikrotik-routeros-ops` + [safe-ssh-mutation.md](../mikrotik-routeros-ops/references/safe-ssh-mutation.md). Toda execução SSH deve preservar transporte, exit, stdout e stderr; evidência incompleta é indeterminada.
