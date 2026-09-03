# secure-rtsp-camera-tools

Arquitetura reutilizável para ferramentas Hermes de snapshot/status RTSP com helper loopback, FFmpeg em container e secrets apenas em runtime.

## Escopo

- snapshots unitários;
- probe real de status por frame;
- plugin Hermes e entrega `MEDIA:`;
- erros sanitizados e sem Base64 no contexto.

## Status

`DEV` — padrão generalizado; exige validação end-to-end na integração alvo.
