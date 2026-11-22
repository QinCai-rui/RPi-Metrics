import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import { Admin } from './Admin'
import { ApiError, api, type History, type Host, type Snapshot, type User } from './api'
import { localTime } from './format'
import { HistoryChart } from './HistoryChart'
import { Readings } from './Readings'
import './style.css'

const statusText: Record<Host['status'], string> = { online: 'Online', stale: 'Stale', unavailable: 'Unavailable' }

function Login({ onLogin }: { onLogin: (user: User) => void }) {
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const values = Object.fromEntries(new FormData(event.currentTarget))
    setPending(true)
    setError('')
    try {
      onLogin(await api<User>('/login', { method: 'POST', body: JSON.stringify(values) }))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPending(false)
    }
  }
  return <main className="login">
    <p className="brand">fleetmuster</p>
    <h1>Sign in</h1>
    <form onSubmit={signIn}>
      <label>Username<input autoComplete="username" name="username" maxLength={64} required /></label>
      <label>Password<input autoComplete="current-password" name="password" type="password" required /></label>
      {error && <p role="alert" className="error">{error}</p>}
      <button className="primary" disabled={pending}>Sign in</button>
    </form>
  </main>
}

function Status({ host }: { host: Host }) {
  return <span className={'host-status ' + host.status}>{statusText[host.status]}</span>
}

function HostPanel({ host, onError }: { host: Host; onError: (error: unknown) => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [history, setHistory] = useState<History | null>(null)
  const [hours, setHours] = useState(6)
  const [error, setError] = useState('')
  const [visible, setVisible] = useState(() => !document.hidden)
  useEffect(() => {
    const onVisibilityChange = () => setVisible(!document.hidden)
    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => document.removeEventListener('visibilitychange', onVisibilityChange)
  }, [])
  useEffect(() => {
    if (!visible) return
    let timer: ReturnType<typeof setTimeout>
    let nextHistory = 0
    const controller = new AbortController()
    const options = { signal: controller.signal }
    async function refresh() {
      const now = performance.now()
      const refreshHistory = now >= nextHistory
      if (refreshHistory) nextHistory = now + 10000
      const results = await Promise.allSettled([
        api<Snapshot>(`/hosts/${host.id}/metrics`, options),
        refreshHistory ? api<History>(`/hosts/${host.id}/history?hours=${hours}`, options) : null,
      ])
      if (controller.signal.aborted) return
      const [metrics, recent] = results
      if (metrics.status === 'fulfilled') setSnapshot(metrics.value)
      if (recent.status === 'fulfilled' && recent.value) setHistory(recent.value)
      const failures = results.flatMap(result => result.status === 'rejected' ? [result.reason] : [])
      if (failures.length) {
        failures.forEach(onError)
        setError('Could not refresh the dashboard. Retrying…')
      } else {
        setError('')
      }
      timer = setTimeout(refresh, 2000)
    }
    void refresh()
    return () => { controller.abort(); clearTimeout(timer) }
  }, [host.id, hours, onError, visible])
  const current = snapshot?.host ?? host
  return <article className="host-panel">
    <header className="host-heading">
      <div><h1>{host.name}</h1>
        {current.observed_hostname && <p>{current.observed_hostname}</p>}</div>
      <div className="contact"><Status host={current} />
        <p>{current.last_contact ? <>Last contact <time dateTime={current.last_contact}>{localTime(current.last_contact)}</time></>
          : 'No contact with the agent yet'}</p></div>
    </header>
    {current.status === 'stale' && <p className="notice" role="status">Could not refresh metrics from the agent. Showing the last saved readings.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {snapshot ? <Readings snapshot={snapshot} /> : !error && <p>Loading readings…</p>}
    <HistoryChart history={history} hours={hours} setHours={value => { setHistory(null); setHours(value) }} />
  </article>
}

function Workspace({ user, onSignOut }: { user: User; onSignOut: () => void }) {
  const [hosts, setHosts] = useState<Host[] | null>(null)
  const [selected, setSelected] = useState('')
  const [showAdmin, setShowAdmin] = useState(false)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    void api<Host[]>('/hosts', { signal: controller.signal }).then(data => {
      setHosts(data)
      setError('')
    }).catch(err => {
      if (controller.signal.aborted) return
      if (err instanceof ApiError && err.status === 401) onSignOut()
      else setError(err.message)
    })
    return () => controller.abort()
  }, [refreshKey, onSignOut])
  const host = hosts?.find(item => item.id === selected) ?? hosts?.[0]
  const hostError = useCallback((err: unknown) => {
    if (err instanceof ApiError && err.status === 401) onSignOut()
    if (err instanceof ApiError && err.status === 404) setRefreshKey(i => i + 1)
  }, [onSignOut])

  async function signOut() {
    try {
      await api('/logout', { method: 'POST' })
      onSignOut()
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) onSignOut()
      else setError((err as Error).message)
    }
  }

  return <>
    <header className="topbar">
      <span className="brand">fleetmuster</span>
      <div><span>{user.username}</span><button onClick={signOut}>Sign out</button></div>
    </header>
    <div className="layout">
      <aside><nav aria-label="Workspace">
        <h2>Hosts</h2>
        {hosts?.map(item => <button key={item.id} className={!showAdmin && item.id === host?.id ? 'selected' : ''}
          aria-current={!showAdmin && item.id === host?.id ? 'page' : undefined}
          onClick={() => { setSelected(item.id); setShowAdmin(false) }}>{item.name}</button>)}
        {hosts?.length === 0 && <p>No hosts assigned</p>}
        {user.role === 'admin' && <button className={showAdmin ? 'selected' : ''} aria-current={showAdmin ? 'page' : undefined}
          onClick={() => setShowAdmin(true)}>Manage users</button>}
      </nav></aside>
      <main className="content">
        {error && <p className="error" role="alert">{error} <button onClick={() => setRefreshKey(i => i + 1)}>Retry</button></p>}
        {showAdmin ? <Admin onAccessChange={() => setRefreshKey(i => i + 1)} />
          : host ? <HostPanel key={host.id} host={host} onError={hostError} />
          : <h1>{hosts ? 'No hosts assigned' : 'Loading hosts…'}</h1>}
      </main>
    </div>
  </>
}

function App() {
  const [user, setUser] = useState<User | null | undefined>(undefined)
  const [error, setError] = useState('')
  const session = useCallback(() => {
    setError('')
    void api<User>('/me').then(setUser).catch(err => {
      if (err instanceof ApiError && err.status === 401) setUser(null)
      else setError(err.message)
    })
  }, [])
  useEffect(session, [session])
  const signOut = useCallback(() => setUser(null), [])
  if (error) return <main className="login"><p role="alert">{error}</p><button onClick={session}>Retry</button></main>
  if (user === undefined) return <main className="login"><p>Loading fleetmuster…</p></main>
  return user ? <Workspace user={user} onSignOut={signOut} /> : <Login onLogin={setUser} />
}

createRoot(document.getElementById('root')!).render(<App />)
