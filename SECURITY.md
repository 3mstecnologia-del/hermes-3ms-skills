# Security Policy

A segurança operacional e a proteção de credenciais são prioridades neste repositório.

## O que consideramos problema de segurança

- Credenciais expostas (senhas, usuários reais de produção)
- Tokens de API ou sessão (GitHub, SNMP, ERP, etc.)
- SNMP communities reais
- Chaves privadas ou certificados com material sensível
- Comandos destrutivos classificados incorretamente como seguros ou rotineiros
- Procedimentos que possam causar impacto não documentado em produção
- Vulnerabilidades em MCP servers (injeção, execução arbitrária, vazamento de secrets)
- Dependências inseguras ou desatualizadas com CVE conhecido relevante

## O que não é vulnerabilidade de segurança neste repo

- Defaults de fábrica documentados em manuais oficiais (ex.: IP/credencial padrão de equipamento)
- Placeholders em exemplos (`<HOST>`, `<PASSWORD>`, etc.)
- Comandos read-only de diagnóstico quando corretamente classificados

## Reporte responsável

**Não abra issues públicas** para vulnerabilidades de segurança, credenciais expostas ou falhas que permitam impacto em produção.

Um canal privado de reporte será definido pela 3MS Tecnologia em versão futura desta política.

Enquanto isso:

- não publique detalhes exploráveis em issues ou pull requests;
- remova imediatamente qualquer secret commitado acidentalmente e notifique os mantenedores por canal privado assim que disponível.

## Boas práticas para contribuidores

- Revise `git diff` antes de cada commit procurando secrets.
- Nunca commite `.env`, backups de configuração ou exports de equipamentos.
- Classifique comandos destrutivos e exija confirmação explícita nas skills.
- Para MCPs, use variáveis de ambiente e `.env.example`; valide entradas quando aplicável.

## Resposta

Os mantenedores avaliarão reportes de segurança assim que um canal oficial estiver configurado. Agradecemos a divulgação responsável.
