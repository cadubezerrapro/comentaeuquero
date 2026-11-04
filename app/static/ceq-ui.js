/* comenta EU QUERO: modais e dropdowns no estilo do painel.
 *
 * Substitui alert/confirm/prompt e o <select> nativo do navegador, que
 * quebravam o visual (janela cinza do sistema, menu do macOS). Um arquivo só,
 * sem dependência, usado pelo painel (script normal) e pelo editor (import).
 *
 *   await CEQ.confirmar('Apagar?', {perigo: true, ok: 'Apagar'})  -> true/false
 *   await CEQ.perguntar('Nome do fluxo', {valor: '', placeholder: '...'}) -> texto|null
 *   await CEQ.avisar('Falhou')
 *   <form data-confirmar="Tem certeza?" data-confirmar-perigo> ... </form>
 *   todo <select> vira dropdown estilizado (data-nativo pra manter o do sistema)
 *
 * Os tokens (--fundo, --texto, --linha, --acento...) são os mesmos do painel e
 * do editor; os valores depois da vírgula só valem se a página não definir.
 */
(function (global) {
  'use strict'
  if (global.CEQ && global.CEQ.__ui) return

  const CSS = `
.ceqk-fundo{position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;
  padding:20px;background:color-mix(in srgb,#000 45%,transparent);backdrop-filter:blur(6px);-webkit-backdrop-filter:blur(6px);
  opacity:0;transition:opacity .16s ease;font-family:var(--font-sans,"Instrument Sans",ui-sans-serif,system-ui,sans-serif)}
.ceqk-fundo.ceqk-on{opacity:1}
.ceqk-caixa{width:100%;max-width:420px;background:var(--fundo,#fff);color:var(--texto,#0a0a0a);
  border:1px solid var(--linha,#e6e6e6);border-radius:14px;padding:22px 22px 18px;
  box-shadow:0 24px 64px -12px rgba(0,0,0,.45),0 2px 6px rgba(0,0,0,.08);
  transform:translateY(8px) scale(.98);transition:transform .18s cubic-bezier(.2,.8,.2,1)}
.ceqk-on .ceqk-caixa{transform:none}
.ceqk-icone{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;margin-bottom:14px;
  background:color-mix(in srgb,var(--acento,#F0561D) 12%,transparent);color:var(--acento,#F0561D)}
.ceqk-perigo .ceqk-icone{background:color-mix(in srgb,var(--erro,#b91c1c) 12%,transparent);color:var(--erro,#b91c1c)}
.ceqk-icone svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round}
.ceqk-titulo{font-size:16px;font-weight:600;letter-spacing:-.01em;margin:0 0 6px;line-height:1.35}
.ceqk-texto{font-size:14px;line-height:1.55;color:var(--suave,#6b6b6b);margin:0;white-space:pre-line;word-break:break-word}
.ceqk-caixa input.ceqk-campo{display:block;width:100%;height:40px;margin:16px 0 0;padding:0 12px;box-sizing:border-box;
  border:1px solid var(--linha,#e6e6e6);border-radius:8px;background:var(--fundo,#fff);color:var(--texto,#0a0a0a);
  font:inherit;font-size:14px;outline:none;transition:border-color .15s,box-shadow .15s}
.ceqk-caixa input.ceqk-campo:focus{border-color:var(--acento,#F0561D);box-shadow:0 0 0 3px color-mix(in srgb,var(--acento,#F0561D) 25%,transparent)}
.ceqk-acoes{display:flex;justify-content:flex-end;gap:8px;margin-top:20px}
.ceqk-caixa button.ceqk-btn{display:inline-flex;align-items:center;justify-content:center;height:36px;padding:0 16px;margin:0;
  border-radius:8px;font:inherit;font-size:14px;font-weight:500;cursor:pointer;white-space:nowrap;opacity:1;
  transition:background .15s,border-color .15s,opacity .15s;border:1px solid var(--linha,#e6e6e6);
  background:transparent;color:var(--texto,#0a0a0a)}
.ceqk-caixa button.ceqk-btn:hover{background:color-mix(in srgb,var(--texto,#0a0a0a) 5%,transparent);opacity:1}
.ceqk-caixa button.ceqk-btn.ceqk-ok{background:var(--texto,#0a0a0a);border-color:var(--texto,#0a0a0a);color:var(--fundo,#fff)}
.ceqk-caixa button.ceqk-btn.ceqk-ok:hover{opacity:.88;background:var(--texto,#0a0a0a)}
.ceqk-perigo button.ceqk-btn.ceqk-ok{background:var(--erro,#b91c1c);border-color:var(--erro,#b91c1c);color:#fff}
.ceqk-perigo button.ceqk-btn.ceqk-ok:hover{background:var(--erro,#b91c1c)}
.ceqk-caixa button.ceqk-btn:focus-visible{outline:2px solid var(--acento,#F0561D);outline-offset:2px}

select.ceqk-escondido{position:absolute!important;width:1px!important;height:1px!important;padding:0!important;margin:0!important;
  overflow:hidden!important;clip:rect(0 0 0 0)!important;clip-path:inset(50%)!important;border:0!important;opacity:0!important;pointer-events:none!important}
button.ceqk-sel{display:flex;align-items:center;justify-content:space-between;gap:8px;width:100%;height:36px;margin-top:6px;
  padding:0 10px 0 12px;border:1px solid var(--linha,#e6e6e6);border-radius:6px;background:var(--fundo,#fff);
  color:var(--texto,#0a0a0a);font:inherit;font-size:14px;font-weight:400;cursor:pointer;text-align:left;opacity:1;
  transition:border-color .15s,box-shadow .15s,background .15s;box-sizing:border-box;white-space:nowrap}
button.ceqk-sel:hover{border-color:color-mix(in srgb,var(--texto,#0a0a0a) 22%,var(--linha,#e6e6e6));opacity:1;background:var(--fundo,#fff)}
button.ceqk-sel:focus-visible,button.ceqk-sel.ceqk-aberto{outline:none;border-color:var(--acento,#F0561D);
  box-shadow:0 0 0 3px color-mix(in srgb,var(--acento,#F0561D) 25%,transparent)}
button.ceqk-sel:disabled{opacity:.55;cursor:default}
.ceqk-sel-txt{overflow:hidden;text-overflow:ellipsis;flex:1;min-width:0}
.ceqk-sel-txt.ceqk-vazio{color:var(--suave,#6b6b6b)}
.ceqk-sel svg{width:16px;height:16px;flex:none;fill:none;stroke:var(--suave,#6b6b6b);stroke-width:1.75;stroke-linecap:round;stroke-linejoin:round;transition:transform .16s}
.ceqk-sel.ceqk-aberto svg{transform:rotate(180deg)}
.ceqk-lista{position:fixed;z-index:2147483001;min-width:160px;max-height:300px;overflow:auto;padding:5px;box-sizing:border-box;
  background:var(--fundo,#fff);color:var(--texto,#0a0a0a);border:1px solid var(--linha,#e6e6e6);border-radius:10px;
  box-shadow:0 16px 40px -10px rgba(0,0,0,.35),0 2px 6px rgba(0,0,0,.06);
  font-family:var(--font-sans,"Instrument Sans",ui-sans-serif,system-ui,sans-serif);font-size:14px;
  opacity:0;transform:translateY(-4px);transition:opacity .12s ease,transform .12s ease}
.ceqk-lista.ceqk-cima{transform:translateY(4px)}
.ceqk-lista.ceqk-on{opacity:1;transform:none}
.ceqk-grupo{padding:8px 10px 4px;font-size:11.5px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--suave,#6b6b6b)}
.ceqk-op{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:6px;cursor:pointer;line-height:1.35;user-select:none}
.ceqk-op.ceqk-ativa{background:color-mix(in srgb,var(--texto,#0a0a0a) 6%,transparent)}
.ceqk-op.ceqk-marcada{font-weight:500}
.ceqk-op.ceqk-off{opacity:.45;cursor:default}
.ceqk-op span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ceqk-op svg{width:15px;height:15px;flex:none;fill:none;stroke:var(--acento,#F0561D);stroke-width:2;stroke-linecap:round;stroke-linejoin:round;visibility:hidden}
.ceqk-op.ceqk-marcada svg{visibility:visible}
@media (prefers-reduced-motion:reduce){.ceqk-fundo,.ceqk-caixa,.ceqk-lista,.ceqk-sel svg{transition:none}}
`

  const ICONES = {
    pergunta: '<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    perigo: '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>',
    editar: '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
    info: '<path d="M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
  }
  const CHEVRON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'
  const CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>'

  function injetaCss() {
    if (document.getElementById('ceqk-css')) return
    const s = document.createElement('style')
    s.id = 'ceqk-css'
    s.textContent = CSS
    ;(document.head || document.documentElement).appendChild(s)
  }

  function el(tag, cls, html) {
    const e = document.createElement(tag)
    if (cls) e.className = cls
    if (html != null) e.innerHTML = html
    return e
  }

  // ---------------- modal ----------------
  let fila = Promise.resolve()

  function modal(tipo, mensagem, op) {
    op = op || {}
    // um modal por vez: dois confirm() seguidos esperam um ao outro
    const p = fila.then(() => abreModal(tipo, mensagem, op))
    fila = p.catch(() => {})
    return p
  }

  function abreModal(tipo, mensagem, op) {
    injetaCss()
    return new Promise((resolve) => {
      const anterior = document.activeElement
      const fundo = el('div', 'ceqk-fundo' + (op.perigo ? ' ceqk-perigo' : ''))
      const caixa = el('div', 'ceqk-caixa')
      caixa.setAttribute('role', tipo === 'avisar' ? 'alertdialog' : 'dialog')
      caixa.setAttribute('aria-modal', 'true')
      const ic = op.perigo ? 'perigo' : tipo === 'perguntar' ? 'editar' : tipo === 'avisar' ? 'info' : 'pergunta'
      caixa.appendChild(el('div', 'ceqk-icone', `<svg viewBox="0 0 24 24" aria-hidden="true">${ICONES[ic]}</svg>`))

      // título + texto: a primeira linha vira título quando não vier um
      let titulo = op.titulo
      let texto = String(mensagem == null ? '' : mensagem)
      if (!titulo) {
        const quebra = texto.indexOf('\n')
        if (quebra > 0) { titulo = texto.slice(0, quebra).trim(); texto = texto.slice(quebra + 1).replace(/^\n+/, '') }
        else { titulo = texto; texto = '' }
      }
      const h = el('h2', 'ceqk-titulo'); h.textContent = titulo; h.id = 'ceqk-t' + Date.now()
      caixa.setAttribute('aria-labelledby', h.id)
      caixa.appendChild(h)
      if (texto) { const pp = el('p', 'ceqk-texto'); pp.textContent = texto; caixa.appendChild(pp) }

      let campo = null
      if (tipo === 'perguntar') {
        campo = el('input', 'ceqk-campo')
        campo.type = 'text'
        campo.value = op.valor == null ? '' : String(op.valor)
        if (op.placeholder) campo.placeholder = op.placeholder
        campo.setAttribute('aria-label', titulo)
        caixa.appendChild(campo)
      }

      const acoes = el('div', 'ceqk-acoes')
      let cancelar = null
      if (tipo !== 'avisar') {
        cancelar = el('button', 'ceqk-btn'); cancelar.type = 'button'
        cancelar.textContent = op.cancelar || 'Cancelar'
        acoes.appendChild(cancelar)
      }
      const ok = el('button', 'ceqk-btn ceqk-ok'); ok.type = 'button'
      ok.textContent = op.ok || (tipo === 'avisar' ? 'Entendi' : tipo === 'perguntar' ? 'Salvar' : 'Confirmar')
      acoes.appendChild(ok)
      caixa.appendChild(acoes)
      fundo.appendChild(caixa)

      const travaScroll = document.documentElement.style.overflow
      document.documentElement.style.overflow = 'hidden'
      document.body.appendChild(fundo)
      requestAnimationFrame(() => fundo.classList.add('ceqk-on'))
      setTimeout(() => { (campo || (op.perigo && cancelar) || ok).focus(); if (campo) campo.select() }, 20)

      let fechado = false
      function fecha(valor) {
        if (fechado) return
        fechado = true
        document.removeEventListener('keydown', tecla, true)
        fundo.classList.remove('ceqk-on')
        document.documentElement.style.overflow = travaScroll
        setTimeout(() => fundo.remove(), 170)
        if (anterior && anterior.focus) { try { anterior.focus({ preventScroll: true }) } catch (_) {} }
        resolve(valor)
      }
      const confirma = () => fecha(tipo === 'perguntar' ? campo.value : true)
      const desiste = () => fecha(tipo === 'perguntar' ? null : tipo === 'avisar' ? undefined : false)

      function tecla(e) {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); desiste() }
        else if (e.key === 'Enter' && (e.target === campo || e.target === ok || !caixa.contains(e.target))) {
          e.preventDefault(); e.stopPropagation(); confirma()
        } else if (e.key === 'Tab') {
          // foco preso dentro do modal
          const focaveis = [campo, cancelar, ok].filter(Boolean)
          const i = focaveis.indexOf(document.activeElement)
          e.preventDefault()
          const prox = e.shiftKey ? (i <= 0 ? focaveis.length - 1 : i - 1) : (i + 1) % focaveis.length
          focaveis[prox].focus()
        }
      }
      document.addEventListener('keydown', tecla, true)
      ok.addEventListener('click', confirma)
      if (cancelar) cancelar.addEventListener('click', desiste)
      fundo.addEventListener('mousedown', (e) => { if (e.target === fundo) desiste() })
    })
  }

  // ---------------- <form data-confirmar> ----------------
  function ligaFormularios() {
    document.addEventListener('submit', async (e) => {
      const form = e.target
      if (!(form instanceof HTMLFormElement) || !form.dataset.confirmar) return
      if (form.__ceqkLiberado) { form.__ceqkLiberado = false; return }
      e.preventDefault()
      e.stopImmediatePropagation()
      const sim = await modal('confirmar', form.dataset.confirmar, {
        perigo: form.hasAttribute('data-confirmar-perigo'),
        ok: form.dataset.confirmarOk || undefined,
      })
      if (!sim) return
      form.__ceqkLiberado = true
      const quem = e.submitter
      if (form.requestSubmit) form.requestSubmit(quem && quem.form === form ? quem : undefined)
      else form.submit()
    }, true)
  }

  // ---------------- dropdown ----------------
  const ligados = new Set()
  let aberto = null   // {sel, botao, lista, itens, ativo}

  function textoDe(sel) {
    const o = sel.options[sel.selectedIndex]
    return o ? (o.label || o.text) : ''
  }

  function atualiza(sel) {
    const b = sel.__ceqk
    if (!b) return
    const t = textoDe(sel)
    const span = b.firstChild
    const vazio = !t || (sel.selectedIndex >= 0 && sel.options[sel.selectedIndex].value === '' && sel.options[sel.selectedIndex].disabled)
    if (span.textContent !== (t || 'Escolher…')) span.textContent = t || 'Escolher…'
    span.classList.toggle('ceqk-vazio', !!vazio)
    if (b.disabled !== sel.disabled) b.disabled = sel.disabled
    if (b.title !== t) b.title = t
    // a largura segue a do select (inline, classe, campo-curto...)
    const estilo = sel.getAttribute('style') || ''
    if (b.__estilo !== estilo) { b.__estilo = estilo; b.style.cssText = estilo }
    for (const c of ['campo-curto']) b.classList.toggle(c, sel.classList.contains(c))
  }

  function liga(sel) {
    if (sel.__ceqk || sel.multiple || sel.size > 1 || sel.hasAttribute('data-nativo')) return
    injetaCss()
    const b = el('button', 'ceqk-sel', '<span class="ceqk-sel-txt"></span>' + CHEVRON)
    b.type = 'button'
    b.setAttribute('aria-haspopup', 'listbox')
    b.setAttribute('aria-expanded', 'false')
    const rotulo = sel.getAttribute('aria-label')
    if (rotulo) b.setAttribute('aria-label', rotulo)
    if (sel.id) {
      // <label for=id> continua apontando pro select; clique nele abre o nosso
      const lb = document.querySelector(`label[for="${CSS_ESC(sel.id)}"]`)
      if (lb) lb.addEventListener('click', (e) => { e.preventDefault(); b.focus(); abre(sel) })
    }
    // margem do select (margin-top etc.) passa pro botão
    const cs = getComputedStyle(sel)
    if (cs.marginTop === '0px') b.style.marginTop = '0'
    sel.__ceqk = b
    sel.classList.add('ceqk-escondido')
    sel.tabIndex = -1
    sel.setAttribute('aria-hidden', 'true')
    sel.insertAdjacentElement('afterend', b)
    b.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); aberto && aberto.sel === sel ? fecha() : abre(sel) })
    b.addEventListener('keydown', (e) => {
      if (['ArrowDown', 'ArrowUp', 'Enter', ' '].includes(e.key) && !aberto) { e.preventDefault(); abre(sel) }
    })
    sel.addEventListener('change', () => atualiza(sel))
    ligados.add(sel)
    atualiza(sel)
  }

  const CSS_ESC = (s) => (global.CSS && CSS.escape ? CSS.escape(s) : String(s).replace(/"/g, '\\"'))

  function abre(sel) {
    fecha()
    if (sel.disabled) return
    const b = sel.__ceqk
    const lista = el('div', 'ceqk-lista')
    lista.setAttribute('role', 'listbox')
    const itens = []
    for (const filho of sel.children) {
      const grupo = filho.tagName === 'OPTGROUP'
      if (grupo) {
        const g = el('div', 'ceqk-grupo'); g.textContent = filho.label; lista.appendChild(g)
      }
      for (const o of grupo ? filho.children : [filho]) {
        if (o.tagName !== 'OPTION' || o.hidden) continue
        const item = el('div', 'ceqk-op', CHECK + '<span></span>')
        item.lastChild.textContent = o.label || o.text
        item.setAttribute('role', 'option')
        const off = o.disabled || (grupo && filho.disabled)
        if (off) item.classList.add('ceqk-off')
        if (o.selected) { item.classList.add('ceqk-marcada'); item.setAttribute('aria-selected', 'true') }
        item.__op = o
        item.addEventListener('mousemove', () => marca(itens.indexOf(item)))
        item.addEventListener('mousedown', (e) => e.preventDefault())
        item.addEventListener('click', () => { if (!off) escolhe(o) })
        lista.appendChild(item)
        itens.push(item)
      }
    }
    document.body.appendChild(lista)
    aberto = { sel, botao: b, lista, itens, ativo: -1, busca: '', buscaT: 0 }
    posiciona()
    b.classList.add('ceqk-aberto')
    b.setAttribute('aria-expanded', 'true')
    const i = itens.findIndex((it) => it.classList.contains('ceqk-marcada'))
    marca(i >= 0 ? i : itens.findIndex((it) => !it.classList.contains('ceqk-off')), true)
    requestAnimationFrame(() => lista.classList.add('ceqk-on'))
  }

  function posiciona() {
    if (!aberto) return
    const r = aberto.botao.getBoundingClientRect()
    const l = aberto.lista
    l.style.minWidth = Math.max(r.width, 160) + 'px'
    l.style.left = Math.min(r.left, window.innerWidth - Math.max(r.width, 160) - 8) + 'px'
    const altura = Math.min(l.scrollHeight, 300)
    const baixo = window.innerHeight - r.bottom
    if (baixo < altura + 12 && r.top > baixo) {
      l.classList.add('ceqk-cima')
      l.style.top = Math.max(8, r.top - altura - 6) + 'px'
    } else {
      l.classList.remove('ceqk-cima')
      l.style.top = (r.bottom + 6) + 'px'
    }
  }

  function marca(i, rolar) {
    if (!aberto || i < 0) return
    aberto.itens.forEach((it, j) => it.classList.toggle('ceqk-ativa', j === i))
    aberto.ativo = i
    if (rolar !== false) aberto.itens[i].scrollIntoView({ block: 'nearest' })
  }

  function escolhe(o) {
    const sel = aberto.sel
    const mudou = !o.selected
    o.selected = true
    fecha(true)
    atualiza(sel)
    if (mudou) {
      // v-model do Vue e os listeners das páginas escutam change/input
      sel.dispatchEvent(new Event('input', { bubbles: true }))
      sel.dispatchEvent(new Event('change', { bubbles: true }))
    }
  }

  function fecha(foca) {
    if (!aberto) return
    const { lista, botao } = aberto
    aberto = null
    botao.classList.remove('ceqk-aberto')
    botao.setAttribute('aria-expanded', 'false')
    lista.classList.remove('ceqk-on')
    setTimeout(() => lista.remove(), 130)
    if (foca) botao.focus()
  }

  function ligaDropdowns() {
    document.addEventListener('keydown', (e) => {
      if (!aberto) return
      const { itens } = aberto
      const anda = (passo) => {
        let i = aberto.ativo
        for (let n = 0; n < itens.length; n++) {
          i = (i + passo + itens.length) % itens.length
          if (!itens[i].classList.contains('ceqk-off')) return marca(i)
        }
      }
      if (e.key === 'ArrowDown') { e.preventDefault(); anda(1) }
      else if (e.key === 'ArrowUp') { e.preventDefault(); anda(-1) }
      else if (e.key === 'Home') { e.preventDefault(); aberto.ativo = -1; anda(1) }
      else if (e.key === 'End') { e.preventDefault(); aberto.ativo = 0; anda(-1) }
      else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault()
        // sem isso o mesmo Enter chega no botão (lista já fechada) e reabre
        e.stopPropagation()
        const it = itens[aberto.ativo]
        if (it && !it.classList.contains('ceqk-off')) escolhe(it.__op); else fecha(true)
      } else if (e.key === 'Escape' || e.key === 'Tab') {
        if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation() }
        fecha(e.key === 'Escape')
      } else if (e.key.length === 1 && !e.metaKey && !e.ctrlKey) {
        // digitar pula pra opção que começa com as letras
        clearTimeout(aberto.buscaT)
        aberto.busca += e.key.toLowerCase()
        aberto.buscaT = setTimeout(() => { if (aberto) aberto.busca = '' }, 600)
        const i = itens.findIndex((it) => !it.classList.contains('ceqk-off') &&
          it.textContent.trim().toLowerCase().startsWith(aberto.busca))
        if (i >= 0) marca(i)
      }
    }, true)
    document.addEventListener('mousedown', (e) => {
      if (aberto && !aberto.lista.contains(e.target) && e.target !== aberto.botao && !aberto.botao.contains(e.target)) fecha()
    }, true)
    window.addEventListener('resize', () => fecha())
    document.addEventListener('scroll', (e) => {
      if (aberto && !aberto.lista.contains(e.target)) posiciona()
    }, true)

    const varre = (raiz) => {
      if (raiz.tagName === 'SELECT') liga(raiz)
      else if (raiz.querySelectorAll) raiz.querySelectorAll('select').forEach(liga)
    }
    varre(document.body)
    // Vue, busca do template e páginas que remontam o <select>: liga os novos e
    // atualiza o texto dos que mudaram de opção por código
    let pendente = false
    new MutationObserver((muds) => {
      for (const m of muds) {
        for (const n of m.addedNodes) if (n.nodeType === 1) varre(n)
      }
      if (pendente) return
      pendente = true
      requestAnimationFrame(() => {
        pendente = false
        for (const sel of ligados) {
          if (!sel.isConnected) {
            if (sel.__ceqk) sel.__ceqk.remove()
            ligados.delete(sel)
            continue
          }
          // o Vue às vezes recria o select fora do lugar: o botão vai junto
          if (sel.nextElementSibling !== sel.__ceqk) sel.insertAdjacentElement('afterend', sel.__ceqk)
          atualiza(sel)
        }
      })
    }).observe(document.body, { childList: true, subtree: true, attributes: true,
      attributeFilter: ['disabled', 'selected', 'style', 'class', 'value'] })
    // valor trocado por código (sel.value = x, v-model) não dispara evento nem mutação
    setInterval(() => { for (const sel of ligados) if (sel.isConnected) atualiza(sel) }, 400)
  }

  function inicia() {
    injetaCss()
    ligaFormularios()
    ligaDropdowns()
  }

  const CEQ = global.CEQ || {}
  Object.assign(CEQ, {
    __ui: true,
    confirmar: (m, op) => modal('confirmar', m, op),
    perguntar: (m, op) => modal('perguntar', m, op),
    avisar: (m, op) => modal('avisar', m, op),
    ligarSelect: liga,
  })
  global.CEQ = CEQ

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', inicia)
  else inicia()
})(typeof window !== 'undefined' ? window : this)
