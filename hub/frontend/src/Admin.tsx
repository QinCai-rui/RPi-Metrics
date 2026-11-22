import { useEffect, useState, type FormEvent } from 'react'
import { api, roles, type User } from './api'

type Accounts = { users: (User & { host_ids: string[] })[]; hosts: { id: string; name: string }[] }

export function Admin({ onAccessChange }: { onAccessChange: () => void }) {
  const [accounts, setAccounts] = useState<Accounts | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [message, setMessage] = useState('')

  async function refresh() {
    setAccounts(await api<Accounts>('/admin/users'))
  }

  useEffect(() => { void refresh().catch(err => setError(err.message)) }, [])

  async function change(action: () => Promise<unknown>, success: string) {
    setPending(true)
    setError('')
    setMessage('')
    try {
      await action()
      await refresh()
      onAccessChange()
      setMessage(success)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPending(false)
    }
  }

  function create(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = event.currentTarget
    const values = Object.fromEntries(new FormData(form))
    void change(async () => {
      await api('/admin/users', { method: 'POST', body: JSON.stringify(values) })
      form.reset()
    }, 'User created.')
  }

  return <section className="admin">
    <h1>Users</h1>
    {error && <p role="alert" className="error">{error}</p>}
    {message && <p role="status">{message}</p>}
    <form className="create-user" onSubmit={create}>
      <h2>Create a user</h2>
      <label>Username<input name="username" required maxLength={64} autoComplete="off" /></label>
      <label>Password<input name="password" type="password" required minLength={12} maxLength={1024}
        autoComplete="new-password" /></label>
      <label>Role<select name="role" defaultValue="viewer">
        {roles.map(role => <option key={role} value={role}>{role}</option>)}
      </select></label>
      <button className="primary" disabled={pending}>Create user</button>
    </form>
    <h2>Host access</h2>
    {accounts ? <ul className="accounts">{accounts.users.map(user => <li key={user.id}>
      <div><strong>{user.username}</strong><p>{user.role}</p></div>
      <div className="grants">{accounts.hosts.map(host => {
        const granted = user.host_ids.includes(host.id)
        return <label key={host.id}>
          <input type="checkbox" checked={granted} disabled={pending}
            aria-label={`${user.username} access to ${host.name}`}
            onChange={() => void change(
              () => api(`/admin/users/${user.id}/hosts/${host.id}`, { method: granted ? 'DELETE' : 'PUT' }),
              granted ? 'Access revoked.' : 'Access granted.',
            )} />
          {host.name}
        </label>
      })}</div>
    </li>)}</ul> : !error && <p>Loading users…</p>}
  </section>
}
