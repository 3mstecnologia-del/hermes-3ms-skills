# olt-intelbras-g08-ops

Skill operacional para **OLT Intelbras G08** (GPON Cassette, 8 portas PON).

## Objetivo

Provisionar, diagnosticar, auditar, monitorar e operar com segurança a OLT G08 e ONTs Intelbras compatíveis, via CLI GPON (`GPON>` / `GPON#`).

## Equipamentos suportados

| Equipamento | Tecnologia | Firmware referência | Testado em equipamento |
|-------------|------------|---------------------|------------------------|
| Intelbras OLT G08 | GPON | V100R001B01D002P001SP9 (manual) | Não — baseado em manual |

## Compatibilidade

- **Não** confundir com OLT 4840 E (EPON) — CLI e profiles são diferentes
- ONTs Intelbras listadas no manual (ex.: i41-100, i40-211, i40-421) — validar `device type ?` no firmware em uso
- Comandos devem ser confirmados com `?` / `help` quando firmware divergir

## Instalação

```bash
cp -a .hermes/skills/3mstecnologia/olt-intelbras-g08-ops ~/.hermes/skills/3mstecnologia/
# ou copiar todo o namespace 3mstecnologia
```

## Fontes / referências

- Intelbras — *Manual de Usuário OLT G08* (material local de estudo, não versionado)
- Intelbras — *MIBs SNMP OLT G08* (OIDs `1.3.6.1.4.1.13464.*`)

## Limitações

- Versão **0.1.0 / DEV**: derivada de documentação; validação em laboratório pendente
- Não reproduz trechos extensos do manual; ver `references/` para cenários e OIDs resumidos

## Segurança

Read-first. Potência óptica de recepção recomendada: **-8 a -28 dBm**. Ações destrutivas exigem confirmação explícita.
