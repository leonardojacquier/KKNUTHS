# Umami — analytics da GNH (Fase 6B)

**Instalação (na VPS, uma vez):**
```bash
cd ~/KKNUTHS && git pull && bash deploy/umami/setup-umami.sh
```
Depois adicione o bloco de `caddy-snippet.txt` ao Caddyfile,
rode `caddy validate` e só então `systemctl reload caddy`.
Aponte o DNS de `stats.vortex369.com.br` para a VPS.

- As 3 páginas do site já carregam o script com o website-id `12bb20da-6e8c-4f0a-8953-5c8c430396f1`
  (enquanto o Umami não estiver no ar, a chamada falha silenciosamente — sem efeito na página).
- Login inicial: admin / umami — **troque a senha**.
- Sem cookies → sem banner de consentimento (LGPD-friendly).
