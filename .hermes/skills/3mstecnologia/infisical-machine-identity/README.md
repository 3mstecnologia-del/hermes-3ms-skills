# infisical-machine-identity

Skill DEV para configurar e validar acesso do Infisical por Machine Identity/Universal Auth sem expor valores de secrets.

## Escopo

- descoberta mínima do endpoint;
- autenticação com credenciais fornecidas em runtime;
- validação por metadados, projetos, ambientes e nomes de chaves;
- persistência local root-only fora de repositórios;
- verificação de caches transitórios do Hermes.

## Segurança

Nunca versionar client ID, client secret, access tokens ou valores recuperados. Use placeholders e o gestor de segredos autorizado. A skill não autoriza mudanças de infraestrutura por si só.

## Estado

`0.1.0` — **DEV**. Revisada de forma estática; requer validação adicional em ambientes controlados antes de status LAB/STABLE.
