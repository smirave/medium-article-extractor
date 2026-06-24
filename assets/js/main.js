marked.setOptions({ breaks: true, gfm: true })

let articles = []
let articleOpen = false
let pollTimer = null

// ── Theme ────────────────────────────────
const prefersDark = window.matchMedia('(prefers-color-scheme:dark)').matches
let dark = localStorage.getItem('theme') === 'dark' || (!localStorage.getItem('theme') && prefersDark)

function applyTheme() {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : '')
    const icon = document.getElementById('theme-icon')
    icon.innerHTML = dark
        ? `<path d="M12.5 9.5A5 5 0 0 1 6.5 3.5a5 5 0 1 0 6 6Z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/>`
        : `<path d="M8 1v1M8 14v1M1 8H2M14 8h1M3.05 3.05l.7.7M12.25 12.25l.7.7M3.05 12.95l.7-.7M12.25 3.75l.7-.7M11 8a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" stroke="currentColor" stroke-width="1.4" stroke-linecap="round"/>`
}

function toggleTheme() {
    dark = !dark
    localStorage.setItem('theme', dark ? 'dark' : 'light')
    applyTheme()
}

applyTheme()

// ── Load articles ────────────────────────
async function load(silent = false) {
    try {
        const res = await fetch('/api/articles')
        articles = await res.json()
        articles.sort((a, b) => (b.meta.date || '').localeCompare(a.meta.date || ''))
        renderGrid(articles)
        document.getElementById('count-bar').textContent =
            `${articles.length} article${articles.length !== 1 ? 's' : ''}`
    } catch (error) {
        console.log(error)
        if (!silent)
            document.getElementById('count-bar').textContent = 'Start server.py first'
    }
}

// ── Grid ─────────────────────────────────
function renderGrid(list) {
    const grid = document.getElementById('grid')
    const noRes = document.getElementById('no-results')
    grid.querySelectorAll('.card').forEach(c => c.remove())

    if (!list.length) { noRes.style.display = 'block'; return }
    noRes.style.display = 'none'

    list.forEach((art, i) => {
        const el = document.createElement('div')
        el.className = 'card'
        el.style.animationDelay = `${i * 40}ms`

        const title = art.meta.title || 'Untitled'
        const author = art.meta.author || ''
        const date = art.meta.date || ''
        const tags = (Array.isArray(art.meta.tags) ? art.meta.tags : []).slice(0, 4)
        const tagH = tags.map(t => `<span class="card-tag">${esc(t)}</span>`).join('')

        el.innerHTML = `
      <div class="card-title">${esc(title)}</div>
      <div class="card-meta">
        ${author ? `<span>${esc(author)}</span>` : ''}
        ${author && date ? '<span class="cdot"></span>' : ''}
        ${date ? `<span>${date}</span>` : ''}
      </div>
      ${tagH ? `<div class="card-tags">${tagH}</div>` : ''}
      <div class="card-footer">
        <div class="card-arrow">
          <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
            <path d="M2 10L10 2M10 8V2H4" stroke="#aaa" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
    `
        el.addEventListener('click', () => openArticle(art))
        grid.appendChild(el)
    })
}

function esc(str = '') {
    return String(str)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;')
}

// FIX: normalize text for Unicode-safe search (handles Persian, Arabic, accented chars)
function normalizeSearch(str) {
    return String(str)
        .normalize('NFC')
        .toLowerCase()
        .trim()
}

// ── Search ───────────────────────────────
document.getElementById('search').addEventListener('input', e => {
    const q = normalizeSearch(e.target.value)
    if (!q) { renderGrid(articles); return }
    renderGrid(articles.filter(a => {
        const t = normalizeSearch(a.meta.title || '')
        const au = normalizeSearch(a.meta.author || '')
        const tg = normalizeSearch((Array.isArray(a.meta.tags) ? a.meta.tags : []).join(' '))
        const b = normalizeSearch(a.body || '')
        return t.includes(q) || au.includes(q) || tg.includes(q) || b.includes(q)
    }))
})

// ── Open / close article ─────────────────
function openArticle(art) {
    const meta = art.meta
    const tags = Array.isArray(meta.tags) ? meta.tags : []
    const imgBase = '/' + art.images_dir.replace(/\\/g, '/')

    const body = (art.body || '')
        .replace(/!\[([^\]]*)\]\(images\/([^)]+)\)/g,
            (_, alt, fname) => `![${alt}](${imgBase}/${fname})`)

    const titlePat = (meta.title || '').replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
    const cleaned = body.replace(new RegExp(`^#\\s*${titlePat}\\s*\n?`, 'm'), '').trim()

    const chips = tags.map(t => `<span class="fm-chip">${esc(t)}</span>`).join('')
    const src = meta.source
        ? `<a href="${meta.source}" target="_blank" class="fm-link">↗ Read on Medium</a>` : ''

    document.getElementById('fm-area').innerHTML = `
    <div class="fm">
      <div class="fm-title">${esc(meta.title || 'Untitled')}</div>
      <div class="fm-byline">
        ${meta.author ? `<strong>${esc(meta.author)}</strong>` : ''}
        ${meta.author && meta.date ? '<span class="fm-sep"></span>' : ''}
        ${meta.date ? `<span>${meta.date}</span>` : ''}
      </div>
      ${chips ? `<div class="fm-chips">${chips}</div>` : ''}
      ${src}
    </div>
  `

    const av = document.getElementById('article-view')
    av.scrollTop = 0
    av.offsetHeight

    document.getElementById('prose').innerHTML = marked.parse(cleaned)
    document.getElementById('grid-view').classList.add('exit')
    av.classList.add('open')
    articleOpen = true
    history.pushState({ article: true }, '')
}

function closeArticle() {
    document.getElementById('article-view').classList.remove('open')
    document.getElementById('grid-view').classList.remove('exit')
    articleOpen = false
}

window.addEventListener('popstate', () => { if (articleOpen) closeArticle() })

// ── Add modal ────────────────────────────
// FIX: always fully reset modal state on open
function resetModal() {
    document.getElementById('modal-default').style.display = 'block'
    document.getElementById('modal-loading').style.display = 'none'
    document.getElementById('url-input').value = ''
}

function openModal() {
    resetModal()
    document.getElementById('modal-overlay').classList.add('open')
    setTimeout(() => document.getElementById('url-input').focus(), 280)
}

// FIX: always clear pollTimer on close to prevent memory leak + double-poll
function closeModal() {
    document.getElementById('modal-overlay').classList.remove('open')
    if (pollTimer) {
        clearInterval(pollTimer)
        pollTimer = null
    }
    // reset after close animation finishes
    setTimeout(resetModal, 300)
}

function overlayClick(e) {
    if (e.target === document.getElementById('modal-overlay')) closeModal()
}

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeModal()
    if (e.key === 'Enter' && document.getElementById('modal-overlay').classList.contains('open'))
        startScrape()
})

async function startScrape() {
    const url = document.getElementById('url-input').value.trim()
    if (!url || !url.startsWith('http')) {
        shake(document.getElementById('url-input')); return
    }

    // FIX: prevent starting a second scrape if one is running
    if (pollTimer) return

    // show loading
    document.getElementById('modal-default').style.display = 'none'
    document.getElementById('modal-loading').style.display = 'block'
    document.getElementById('loading-url-text').textContent = url

    try {
        const r = await fetch('/api/scrape', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url })
        })
        const d = await r.json()
        if (!d.ok) throw new Error(d.error || 'Failed')
    } catch (e) {
        closeModal()
        toast('⚠ ' + e.message); return
    }

    // poll until done
    pollTimer = setInterval(async () => {
        try {
            const s = await (await fetch('/api/scrape/status')).json()
            if (!s.running) {
                clearInterval(pollTimer); pollTimer = null
                closeModal()
                await load(true)
                toast('✓ Article added!')
            }
        } catch {
            // FIX: also clear timer on network error during polling
            clearInterval(pollTimer); pollTimer = null
            closeModal()
            toast('⚠ Connection lost')
        }
    }, 1200)
}

function shake(el) {
    el.style.animation = 'none'; el.offsetHeight
    el.style.animation = 'shake .35s ease'
}

// ── Toast ────────────────────────────────
function toast(msg, dur = 2800) {
    const t = document.getElementById('toast')
    t.textContent = msg
    t.classList.add('show')
    setTimeout(() => t.classList.remove('show'), dur)
}

// ── Shake keyframe ───────────────────────
const st = document.createElement('style')
st.textContent = '@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-6px)}75%{transform:translateX(6px)}}'
document.head.appendChild(st)

load()