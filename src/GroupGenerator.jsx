import { useEffect, useMemo, useRef, useState } from 'react'
import './GroupGenerator.css'

const COLORS = ['#2b50e8', '#e0611f', '#1f9d6b', '#c02f8f', '#8a5cf6', '#d1a100', '#0f9cc0', '#d6373b']

const NATIONS = [
  'Skånes',
  'Södermanlands-Nerikes Nation',
  'Smålands Nation',
  'Göteborgs Nation',
  'Uplands Nation',
  'Värmlands Nation',
  'Stockholms Nation',
  'Gästrike-Hälsingland Nation',
  'Östgöta Nation',
  'Kalmar Nation',
  'Västgöta Nation',
  'Norrlands Nation',
  'Västmanlands-Dala Nation',
]

// One path is an ordered list of pub names.
// (A stop that arrives as an object with a name is accepted too.)
function normalizePath(path) {
  return (Array.isArray(path) ? path : []).map(s =>
    String(s && typeof s === 'object' ? (s.name ?? s.pub ?? s.nation ?? '') : (s ?? '')))
}

// `paths` from /api/generate-path is a list of such paths.
function normalizePaths(paths) {
  return (Array.isArray(paths) ? paths : []).map(normalizePath)
}

function detectDelimiter(text) {
  const first = text.split(/\r?\n/)[0] || ''
  const counts = [',', ';', '\t'].map(d => [d, first.split(d).length - 1])
  counts.sort((a, b) => b[1] - a[1])
  return counts[0][1] > 0 ? counts[0][0] : ','
}

function parseCSV(text, d) {
  const out = []
  let row = [], cur = '', q = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (q) {
      if (ch === '"' && text[i + 1] === '"') { cur += '"'; i++ }
      else if (ch === '"') q = false
      else cur += ch
    } else if (ch === '"') q = true
    else if (ch === d) { row.push(cur); cur = '' }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i++
      row.push(cur); out.push(row); row = []; cur = ''
    } else cur += ch
  }
  if (cur !== '' || row.length) { row.push(cur); out.push(row) }
  return out.filter(r => r.some(c => c.trim() !== ''))
}

function labelsFor(rows, hasHeader) {
  if (!rows.length) return []
  const width = Math.max(...rows.map(r => r.length))
  return Array.from({ length: width }, (_, i) =>
    hasHeader && rows[0][i] && rows[0][i].trim() ? rows[0][i].trim() : 'Column ' + (i + 1))
}

export default function App() {
  const [file, setFileState] = useState(null)
  const [rows, setRows] = useState([])
  const [delimiter, setDelimiter] = useState(',')
  const [hasHeader, setHasHeader] = useState(true)
  const [nameCol, setNameCol] = useState('0')
  const [partnerCol, setPartnerCol] = useState('')
  const [n, setN] = useState(3)
  const [groups, setGroups] = useState([])
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const [over, setOver] = useState(false)
  const [copyLabel, setCopyLabel] = useState('Copy as text')
  const [api, setApi] = useState('https://pubcrawl-groups.onrender.com')
  const [selected, setSelected] = useState(NATIONS)
  const [startStop, setStartStop] = useState(NATIONS[0])
  const [routes, setRoutes] = useState([])
  const [routePool, setRoutePool] = useState(0) 
    // how many different routes the backend returned
  const fileInput = useRef(null)
  // Remembers routes already fetched, so shuffling again doesn't hit the routing API again.
  const pathCache = useRef(new Map())

  const labels = useMemo(() => labelsFor(rows, hasHeader), [rows, hasHeader])

  const effectiveStart = selected.includes(startStop)
  ? startStop
  : (selected[0] || '')

  // stop the browser opening a file dropped outside the zone
  useEffect(() => {
    const stop = e => e.preventDefault()
    window.addEventListener('dragover', stop)
    window.addEventListener('drop', stop)
    return () => {
      window.removeEventListener('dragover', stop)
      window.removeEventListener('drop', stop)
    }
  }, [])

  async function setFile(f) {
    if (!f) return
    if (!/\.csv$/i.test(f.name) && f.type !== 'text/csv') {
      setMsg('That is not a CSV file. Choose a .csv file.')
      return
    }
    const text = (await f.text()).replace(/^\uFEFF/, '')
    const d = detectDelimiter(text)
    const parsed = parseCSV(text, d)
    if (!parsed.length) { setMsg('That file is empty.'); return }

    const ls = labelsFor(parsed, hasHeader)
    const p = ls.findIndex(l => /partner|pair|friend|with|kompis|vän|par\b/i.test(l))
    const nm = ls.findIndex(l => /name|namn/i.test(l))
    const nameIdx = nm >= 0 ? nm : 0

    setDelimiter(d)
    setRows(parsed)
    setFileState(f)
    setMsg('')
    setNameCol(String(nameIdx))
    setPartnerCol(p >= 0 && p !== nameIdx ? String(p) : '')
  }

  // POST /api/generate-path  { pubs: [...], start: "..." }  ->  { start, paths: [[...], ...], total_stops }
  function fetchPaths(base, pubs, start) {
    const cache = pathCache.current
    const key = JSON.stringify([base, pubs, start])
    if (!cache.has(key)) {
      const p = (async () => {
        const res = await fetch(base + '/api/generate-path', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ pubs, start }),
        })
        const data = await res.json().catch(() => ({}))
        if (!res.ok) throw new Error(data.error || 'Server error ' + res.status)
        return normalizePaths(data.paths)
      })()
      p.catch(() => cache.delete(key))   // don't remember failures
      cache.set(key, p)
    }
    return cache.get(key)
  }

  async function generate() {
    if (!file) { setMsg('Choose a CSV file first.'); return }
    if (!n || n < 1) { setMsg('Enter at least 1 group.'); return }
    if (nameCol === partnerCol) { setMsg('Name and partner must be different columns.'); return }
    if (selected.length < 2) { setMsg('Pick at least two nations to make a route.'); return }
    const base = api.replace(/\/$/, '')
    const pubs = NATIONS.filter(x => selected.includes(x))

    const fd = new FormData()
    fd.append('file', file)
    fd.append('num_groups', n)
    fd.append('name_col', nameCol)          // 0-based index
    fd.append('partner_col', partnerCol)    // '' = no partners
    fd.append('has_header', hasHeader)      // 'true' / 'false'
    fd.append('delimiter', delimiter)       // ',' ';' or tab

    setBusy(true)
    setMsg('')
    try {
      const res = await fetch(base + '/api/generate-groups', { method: 'POST', body: fd })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Server error ' + res.status)

      // show the groups right away; routes fill in when they arrive (null = still loading)
      setRoutes(data.groups.map(() => null))
      setRoutePool(0)
      setGroups(data.groups)

      // one request returns several routes; group i gets route i (wrapping if there are more groups)
      let pool = []
      try {
        pool = await fetchPaths(base, pubs, effectiveStart)
      } catch (err) {
        setMsg(err instanceof TypeError
          ? 'Could not fetch routes. Check that the backend at ' + api + ' is running and allows JSON requests (CORS).'
          : 'Route error: ' + err.message)
      }
      setRoutePool(pool.length)
      setRoutes(data.groups.map((_, i) => (pool.length ? pool[i % pool.length] : [])))
    } catch (err) {
      setMsg(err instanceof TypeError
        ? 'Could not reach the backend. Check that main.py is running at ' + api + '.'
        : 'Backend error: ' + err.message)
    } finally {
      setBusy(false)
    }
  }

  async function copyText() {
    const text = groups.map((g, i) => {
      const stops = routes[i] || []
      const route = stops.length ? '\n  Route: ' + stops.join(' → ') : ''
      return `Group ${i + 1}\n` + g.map(x => '  ' + x).join('\n') + route
    }).join('\n\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopyLabel('Copied')
    } catch {
      setCopyLabel('Copy failed')
    }
    setTimeout(() => setCopyLabel('Copy as text'), 1500)
  }

  const bodyStart = hasHeader ? 1 : 0
  const previewRows = rows.slice(bodyStart, bodyStart + 4)
  const cls = i => (String(i) === nameCol ? 'selName' : String(i) === partnerCol ? 'selPartner' : '')
  const total = groups.reduce((s, g) => s + g.length, 0)

  return (
    <main>
      <section className="panel" aria-label="Settings">
        <div>
          <h1>Group generator</h1>
          <p className="sub">Upload your list, choose the columns to read, and mutual pairs stay together.</p>
        </div>

        <div
          id="drop"
          className={(over ? 'over ' : '') + (file ? 'has' : '')}
          tabIndex={0}
          role="button"
          aria-label="Choose CSV file"
          onClick={() => fileInput.current.click()}
          onKeyDown={e => {
            if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.current.click() }
          }}
          onDragEnter={e => { e.preventDefault(); setOver(true) }}
          onDragOver={e => { e.preventDefault(); setOver(true) }}
          onDragLeave={e => { e.preventDefault(); setOver(false) }}
          onDrop={e => { e.preventDefault(); setOver(false); setFile(e.dataTransfer.files[0]) }}
        >
          <strong>{file ? file.name : 'Drop a CSV file here'}</strong>
          <small>{file ? 'Click or drop to replace' : 'or click to browse'}</small>
          <input
            ref={fileInput}
            type="file"
            accept=".csv,text/csv"
            hidden
            onClick={e => e.stopPropagation()}
            onChange={e => { setFile(e.target.files[0]); e.target.value = '' }}
          />
        </div>

        <div id="mapping">
            <label className="check">
              <input type="checkbox" checked={hasHeader} onChange={e => setHasHeader(e.target.checked)} /> First row is a header
            </label>
            <div className="field">
              <label htmlFor="nameCol">Name column</label>
              <select id="nameCol" value={nameCol} onChange={e => setNameCol(e.target.value)}>
                {labels.map((l, i) => <option key={i} value={i}>{l}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="partnerCol">Partner column <small>(optional)</small></label>
              <select id="partnerCol" value={partnerCol} onChange={e => setPartnerCol(e.target.value)}>
                {rows.length > 0 && <option value="">None</option>}
                {labels.map((l, i) => <option key={i} value={i}>{l}</option>)}
              </select>
            </div>
            <div className="preview">
              <table id="preview">
                <tbody>
                  <tr>{labels.map((l, i) => <th key={i} className={cls(i)}>{l}</th>)}</tr>
                  {previewRows.map((r, ri) => (
                    <tr key={ri}>{labels.map((_, i) => <td key={i} className={cls(i)}>{r[i]}</td>)}</tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        <div role="group" aria-labelledby="nationsLabel">
  <div className="nhead">
    <span id="nationsLabel" className="lbl">
      Nations <small>({selected.length} of {NATIONS.length} selected)</small>
    </span>
    <span className="nlinks">
      <button type="button" className="linkbtn" onClick={() => setSelected(NATIONS)}>All</button>
      <button type="button" className="linkbtn" onClick={() => setSelected([])}>None</button>
    </span>
  </div>

  {/* Displays which nation is currently selected as start */}
  {effectiveStart && (
    <p style={{ margin: '0.4rem 0', fontSize: '0.85rem', color: '#555' }}>
      Starting stop: <strong>{effectiveStart}</strong>
    </p>
  )}

  <div className="nations">
    {NATIONS.map(nation => {
      const isSelected = selected.includes(nation)
      const isStart = effectiveStart === nation

      return (
        <div
          key={nation}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '0.5rem',
            padding: '2px 0'
          }}
        >
          <label className="check" style={{ margin: 0 }}>
            <input
              type="checkbox"
              checked={isSelected}
              onChange={e => {
                const next = e.target.checked
                  ? NATIONS.filter(x => x === nation || selected.includes(x))
                  : selected.filter(x => x !== nation)
                setSelected(next)
                // If unchecking the current start, fallback to another selected nation
                if (!e.target.checked && startStop === nation) {
                  setStartStop(next[0] || '')
                }
              }}
            />
            {nation}
          </label>

          {/* Button to designate this stop as the starting point */}
          {isSelected && (
            <button
              type="button"
              className={isStart ? 'start-btn active' : 'start-btn'}
              onClick={() => setStartStop(nation)}
              title={`Set ${nation} as start stop`}
            >
              {isStart ? '★ Start' : 'Set start'}
            </button>
          )}
        </div>
      )
    })}
  </div>
</div>
        <div>
          <label htmlFor="n">Number of groups</label>
          <div className="stepper">
            <button type="button" aria-label="Fewer groups" onClick={() => setN(Math.max(1, (+n || 1) - 1))}>−</button>
            <input
              id="n"
              type="number"
              min="1"
              value={n}
              onChange={e => setN(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
            />
            <button type="button" aria-label="More groups" onClick={() => setN((+n || 0) + 1)}>+</button>
          </div>
        </div>

        <button className="primary" disabled={!file || busy} onClick={generate}>
          {busy ? 'Generating…' : 'Generate groups'}
        </button>
        <p id="msg" role="alert">{msg}</p>

        <details>
          <summary>Backend address</summary>
          <input type="text" value={api} aria-label="Backend address" onChange={e => setApi(e.target.value)} />
        </details>
      </section>

      <section aria-live="polite">
        <div id="results">
          {groups.length === 0 ? (
            <div className="empty">Your groups will show up here.</div>
          ) : (
            <>
              <div className="head">
                <h2>{groups.length} groups, {total} people</h2>
                <div className="actions">
                  <button onClick={generate} disabled={busy}>Shuffle again</button>
                  <button onClick={copyText}>{copyLabel}</button>
                </div>
              </div>
              {routePool > 0 && routePool < groups.length && (
                <p className="note">
                  Only {routePool} different routes for {groups.length} groups, so some groups share a route.
                </p>
              )}
              <div id="grid">
                {groups.map((g, i) => (
                  <div className="card" key={i} style={{ '--c': COLORS[i % COLORS.length] }}>
                    <h3><b>Group {i + 1}</b><span>{g.length} people</span></h3>
                    <ul>{g.map((name, j) => <li key={j}>{name}</li>)}</ul>
                    <div className="route">
                      <h4>Route{routes[i]?.length > 0 && <small> · {routes[i].length} stops</small>}</h4>
                      {routes[i] == null ? (
                        <p className="noroute">Planning route…</p>
                      ) : routes[i].length === 0 ? (
                        <p className="noroute">No route returned for this group.</p>
                      ) : (
                        <ol>
                          {routes[i].map((s, k) => <li key={k}><span className="stop">{s}</span></li>)}
                        </ol>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </section>
    </main>
  )
}