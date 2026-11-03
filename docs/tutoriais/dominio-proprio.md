# Domínio próprio

Usar `ceq.sualoja.com.br` em vez do endereço que veio na instalação.

## Docker manual ou computador

1. Crie o registro DNS (`A` para o IP da VPS, ou a rota do túnel da Cloudflare com `cloudflared tunnel route dns`).
2. Ponha o domínio no Caddy (ou nginx) e recarregue. Veja o [Docker manual](../instalar/docker.md).
3. Troque o `BASE_URL` no `.env` e rode `docker compose up -d`.
4. Na Meta, troque o endereço nos três lugares:
   - **URL de callback do webhook** (e do webhook do WhatsApp, se usar): `https://NOVO-ENDERECO/webhook`
   - **URI de redirecionamento** em "Configurar o login da empresa": `https://NOVO-ENDERECO/auth/callback`
   - **URL da Política de Privacidade**: `https://NOVO-ENDERECO/privacy`
5. Entre no painel pelo endereço novo. O login antigo não vale no domínio novo; é só entrar de novo.

> [!WARNING]
> **Ordem importa**
>
> Só troque na Meta depois que o endereço novo abrir no navegador com HTTPS. A Meta testa a URL do webhook na hora de salvar.
