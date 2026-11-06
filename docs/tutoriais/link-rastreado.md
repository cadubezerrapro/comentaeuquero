# Link rastreado e quem deixou de seguir

A Meta não avisa quando alguém toca no link de uma DM, nem quando alguém deixa de seguir a conta. A partir da 1.15.0 o comenta EU QUERO mede as duas coisas, com cuidado para não chamar atenção dos filtros de spam do Instagram.

## Quem abriu o link

### Como funciona (modo padrão: `parametro`)

O link que a pessoa recebe continua sendo o endereço real do seu site. Ele só ganha um `?ceq=<token>` no fim, como um UTM:

```
https://ia-thefuture.vercel.app/?ceq=Xk3v9QpL2aZb#item-tut-clonar-viral
```

Quando a página abre, o seu site avisa o comenta EU QUERO. O clique entra no funil do fluxo, na etapa **clicaram**.

**Por que não um redirecionamento (`seudominio/r/xyz`):** link que leva a pessoa para um domínio diferente do que aparece na mensagem é um dos padrões que a política de spam da Meta trata como suspeito, ainda mais quando o domínio é um subdomínio de hospedagem compartilhada. Com o parâmetro, o domínio que a pessoa vê é o que ela abre.

### Passo 1: diga quais domínios são seus

Nas variáveis do servidor (na Railway: Variables):

```
CEQ_LINK_DOMINIOS=ia-thefuture.vercel.app
```

Só links para esses domínios ganham o `?ceq=`. Link para YouTube, Hotmart ou qualquer outro site sai do jeito que você escreveu. Sem a variável, nenhum link muda.

### Passo 2: cole o aviso no seu site

No HTML do site de destino, antes do `</body>` (troque o endereço pelo da sua instância):

```html
<script>
(function () {
  var t = new URLSearchParams(location.search).get("ceq");
  if (!t || !/^[A-Za-z0-9_-]{8,32}$/.test(t)) return;
  try {
    navigator.sendBeacon("https://comentaeuquero.up.railway.app/r/" + t + "/visto");
  } catch (e) {}
  // tira o token da barra de endereço: se a pessoa compartilhar o link,
  // quem abrir depois não conta como ela
  var u = new URL(location.href);
  u.searchParams.delete("ceq");
  history.replaceState(null, "", u.pathname + u.search + u.hash);
})();
</script>
```

O aviso só é aceito vindo de um domínio de `CEQ_LINK_DOMINIOS`. Abrir de novo dentro de 30 minutos não conta como outro clique. O robô de prévia da Meta não roda JavaScript, então não infla a contagem.

### Link mágico (material liberado só pra quem pediu)

Com `LINK_MAGICO_SEGREDO` igual no servidor do comenta EU QUERO e na Vercel do ia_thefuture, o link de um material (`…/#item-<id>`) sai assim:

```
https://ia-thefuture.vercel.app/?ceq=Xk3v9QpL2aZb&mg=1767225600.9f2c…#item-tut-clonar-viral
```

- `mg` = validade (segundos desde 1970) + HMAC-SHA256 de `<ceq>.<item>.<validade>` com o segredo.
- O site confere a assinatura e libera **só aquele material**, sem login, até a validade (`LINK_MAGICO_DIAS`, padrão 30). O resto continua pedindo cadastro.
- Cada pessoa recebe o seu (o `ceq` é dela). Mexer no item, no código ou na data invalida o link.
- Achou um link repassado? Cole o código `ceq` na busca de **Leads**: aparece quem recebeu.

Gerar um segredo (no CMD, com Python instalado): `python -c "import secrets; print(secrets.token_urlsafe(32))"`. Coloque o mesmo valor nos dois lados e não mande pra ninguém.

### Modo `redirecionar` (opcional)

`CEQ_LINK_RASTREADO=redirecionar` faz o link passar por `BASE_URL/r/<token>`, que conta e manda (302) para o destino. Funciona com qualquer site, sem colar nada, mas é o formato que os filtros olham com mais desconfiança. Se usar, prefira `BASE_URL` num [domínio próprio](./dominio-proprio.md). O robô de prévia recebe o mesmo destino que a pessoa (entregar outra coisa para ele seria cloaking); ele só não conta.

`CEQ_LINK_RASTREADO=desligado` desliga tudo.

## Quem deixou de seguir

Uma vez por dia (`CEQ_RECONSULTA_HORAS`), uma tarefa de fundo reconfere quem constava como seguidor e tem a etiqueta `isca_viral` (`CEQ_RECONSULTA_TAGS`). Quem deixou de seguir:

- ganha a etiqueta `deixou_de_seguir`;
- fica com a data na lista de Leads (coluna Segue) e no CSV (`deixou_de_seguir_em`).

Se a pessoa voltar a seguir, a etiqueta sai e a data fica como histórico.

Para rodar agora, sem esperar o dia: `POST /api/seguidores/reconsultar` (logado).

### Os cuidados que a tarefa tem

- **Só lê.** Nunca manda mensagem para quem deixou de seguir. Cobrar unfollow por DM é o tipo de automação que vira denúncia.
- **Devagar.** Um perfil a cada 3 segundos, no máximo 150 por rodada.
- **Para no primeiro sinal da Meta.** Código de limite, uso acima de 60% nos medidores de rate limit, token inválido: a rodada para, e no caso do limite o envio de mensagens também espera (mesmo freio que o motor já usa). Mensagem tem prioridade sobre esta tarefa.
- **Não chuta.** Se a Meta não informar o status (alguns perfis, ou quem bloqueou a conta), o lead fica como desconhecido (—), nunca como "segue". Erro de rede não muda nada; o lead volta na próxima rodada.
- A Meta só mostra o perfil de quem já mandou mensagem para a conta. Quem só comentou fica fora.
