import { useState } from 'react'
import { LoaderCircle, LockKeyhole, ShoppingBag } from 'lucide-react'

export default function AuthScreen({ onSubmit }) {
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [working, setWorking] = useState(false)

  const submit = async (event) => {
    event.preventDefault()
    setWorking(true); setError('')
    try { await onSubmit(mode, { email, password }) }
    catch (nextError) { setError(nextError.message) }
    finally { setWorking(false) }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-canvas p-5 text-ink transition-colors duration-500">
      <section className="w-full max-w-sm rounded-3xl border border-stone-200 bg-white p-7 shadow-card dark:border-stone-700 dark:bg-stone-900">
        <div className="grid size-12 place-items-center rounded-2xl bg-lime"><ShoppingBag className="size-6 text-stone-950" /></div>
        <p className="mt-6 text-sm font-semibold text-stone-500">Your personal grocery space</p>
        <h1 className="mt-1 text-3xl font-black tracking-tight">Voice Cart</h1>
        <p className="mt-2 text-sm text-stone-500">{mode === 'login' ? 'Sign in to see your list and previous orders.' : 'Create an account to keep every order private.'}</p>
        <form onSubmit={submit} className="mt-6 space-y-3">
          <label className="block text-sm font-semibold">Email<input required type="email" value={email} onChange={event => setEmail(event.target.value)} className="mt-1.5 w-full rounded-xl border border-stone-200 bg-white px-3 py-3 font-normal outline-none focus:border-ink dark:border-stone-700 dark:bg-stone-800" placeholder="you@example.com" /></label>
          <label className="block text-sm font-semibold">Password<input required minLength="8" type="password" value={password} onChange={event => setPassword(event.target.value)} className="mt-1.5 w-full rounded-xl border border-stone-200 bg-white px-3 py-3 font-normal outline-none focus:border-ink dark:border-stone-700 dark:bg-stone-800" placeholder="At least 8 characters" /></label>
          {error && <p className="rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</p>}
          <button disabled={working} className="flex w-full items-center justify-center gap-2 rounded-xl bg-stone-950 px-4 py-3 font-bold text-white transition hover:opacity-90 disabled:opacity-60">{working ? <LoaderCircle className="size-4 animate-spin" /> : <LockKeyhole className="size-4" />}{mode === 'login' ? 'Sign in' : 'Create account'}</button>
        </form>
        <button type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }} className="mt-5 w-full text-sm font-semibold text-stone-500 hover:text-ink">{mode === 'login' ? 'New here? Create an account' : 'Already have an account? Sign in'}</button>
      </section>
    </main>
  )
}
