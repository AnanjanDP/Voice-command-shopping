import { useCallback, useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ClipboardList, Globe2, LoaderCircle, LogOut, Moon, PackageCheck, Plus, ShoppingBag, Sparkles, Sun, Trash2, Volume2 } from 'lucide-react'
import { api, hasAccessToken, setAccessToken } from './api'
import { useSpeechRecognition } from './hooks'
import VoiceOrb from './components/VoiceOrb'
import ItemRow from './components/ItemRow'
import AuthScreen from './components/AuthScreen'

const LANGUAGES = [['en-US', 'English'], ['hi-IN', 'हिन्दी']]

function speak(message, language) {
  if (!('speechSynthesis' in window)) return
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(message)
  utterance.lang = language
  window.speechSynthesis.speak(utterance)
}

function statusClass(status) {
  return { placed: 'bg-amber-100 text-amber-800', delivered: 'bg-emerald-100 text-emerald-800', cancelled: 'bg-stone-200 text-stone-700' }[status] || 'bg-stone-100 text-stone-700'
}

export default function App() {
  const [items, setItems] = useState([])
  const [suggestions, setSuggestions] = useState([])
  const [orders, setOrders] = useState([])
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)
  const [language, setLanguage] = useState('en-US')
  const [status, setStatus] = useState('Ready when you are.')
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [manualValue, setManualValue] = useState('')
  const [themePreference, setThemePreference] = useState(localStorage.getItem('voice-cart-theme') || 'auto')
  const isNight = new Date().getHours() >= 18 || new Date().getHours() < 6
  const isDark = themePreference === 'dark' || (themePreference === 'auto' && isNight)

  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDark)
    localStorage.setItem('voice-cart-theme', themePreference)
  }, [isDark, themePreference])

  const load = useCallback(async () => {
    if (!hasAccessToken()) return
    try {
      const [nextItems, nextSuggestions, nextOrders] = await Promise.all([api.items(), api.suggestions(), api.orders()])
      setItems(nextItems); setSuggestions(nextSuggestions); setOrders(nextOrders)
    } catch (error) {
      if (error.message === 'Sign in to continue.') { setAccessToken(''); setUser(null) }
      else setStatus(error.message === 'Failed to fetch' ? 'Connect the API to start shopping.' : error.message)
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    const restoreSession = async () => {
      if (!hasAccessToken()) { setAuthLoading(false); return }
      try { setUser(await api.me()); await load() }
      catch { setAccessToken('') }
      finally { setAuthLoading(false) }
    }
    restoreSession()
  }, [load])

  const handleAuth = async (mode, credentials) => {
    const result = mode === 'login' ? await api.login(credentials) : await api.register(credentials)
    setAccessToken(result.access_token)
    setUser(result.user)
    setLoading(true)
    await load()
  }

  const runCommand = useCallback(async (transcript) => {
    if (!transcript || working) return
    setWorking(true); setStatus(`Heard: “${transcript}”`)
    try {
      const result = await api.command(transcript, language)
      setStatus(result.message); speak(result.message, language); await load()
    } catch (error) { setStatus(error.message) }
    finally { setWorking(false) }
  }, [language, load, working])

  const handleSpeechError = useCallback((error) => {
    const messages = { 'not-allowed': 'Microphone permission is needed for voice commands.', 'no-speech': 'I didn’t hear anything. Tap the mic and try again.', network: 'Speech recognition needs a network connection in this browser.' }
    setStatus(messages[error] || `Voice input error: ${error}.`)
  }, [])

  const { supported, isListening, interim, toggle } = useSpeechRecognition({ language, onResult: runCommand, onError: handleSpeechError })

  const updateItem = async (id, changes) => {
    const previous = items; setItems(current => current.map(item => item.id === id ? { ...item, ...changes } : item))
    try { await api.updateItem(id, changes) } catch (error) { setItems(previous); setStatus(error.message) }
  }
  const deleteItem = async (id) => {
    const previous = items; setItems(current => current.filter(item => item.id !== id))
    try { await api.deleteItem(id); setStatus('Item removed.') } catch (error) { setItems(previous); setStatus(error.message) }
  }
  const addSuggestion = async (suggestion) => {
    setWorking(true)
    try { const created = await api.addItem(suggestion); setItems(current => [created, ...current]); setSuggestions(current => current.filter(item => item.name !== suggestion.name)); setStatus(`Added ${suggestion.name}.`) }
    catch (error) { setStatus(error.message) }
    finally { setWorking(false) }
  }
  const addManual = async (event) => { event.preventDefault(); const name = manualValue.trim(); if (!name) return; await runCommand(`Add ${name}`); setManualValue('') }
  const clear = async () => {
    if (!items.length || !window.confirm('Clear every item from your list?')) return
    try { await api.clear(); setItems([]); setStatus('Your shopping list is clear.'); await load() } catch (error) { setStatus(error.message) }
  }
  const placeOrder = async () => {
    if (!items.some(item => !item.is_checked) || !window.confirm('Place this order? It will move pending items to your order history.')) return
    setWorking(true)
    try { const order = await api.placeOrder(); setStatus(`Order #${order.id} is placed.`); speak(`Order number ${order.id} is placed.`, language); await load() }
    catch (error) { setStatus(error.message) }
    finally { setWorking(false) }
  }
  const updateOrder = async (id, nextStatus) => {
    try { const updated = await api.updateOrder(id, nextStatus); setOrders(current => current.map(order => order.id === id ? updated : order)); setStatus(`Order #${id} marked ${nextStatus}.`) }
    catch (error) { setStatus(error.message) }
  }
  const logout = () => { setAccessToken(''); setUser(null); setItems([]); setSuggestions([]); setOrders([]); setLoading(false) }

  const groupedItems = useMemo(() => items.reduce((groups, item) => ({ ...groups, [item.category]: [...(groups[item.category] || []), item] }), {}), [items])
  const remaining = items.filter(item => !item.is_checked).length
  const nextTheme = themePreference === 'auto' ? 'light' : themePreference === 'light' ? 'dark' : 'auto'
  const themeLabel = themePreference === 'auto' ? `Auto (${isDark ? 'night' : 'day'})` : themePreference

  if (authLoading) return <main className="grid min-h-screen place-items-center bg-canvas text-ink"><LoaderCircle className="size-6 animate-spin" /></main>
  if (!user) return <AuthScreen onSubmit={handleAuth} />

  return (
    <main className="mx-auto min-h-screen max-w-xl bg-canvas px-4 pb-12 pt-6 text-ink transition-colors duration-500 sm:px-6">
      <header className="flex items-start justify-between gap-3"><div><p className="text-sm font-medium text-stone-500">Hi, {user.email.split('@')[0]}</p><h1 className="text-3xl font-black tracking-tight">Voice Cart</h1></div><div className="flex items-center gap-1"><button type="button" title={`Theme: ${themeLabel}`} onClick={() => setThemePreference(nextTheme)} className="grid size-9 place-items-center rounded-xl border border-stone-200 bg-white text-stone-600 shadow-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300">{isDark ? <Moon className="size-4" /> : <Sun className="size-4" />}</button><label className="flex items-center gap-1 rounded-xl border border-stone-200 bg-white px-2 py-2 text-xs font-semibold text-stone-600 shadow-sm dark:border-stone-700 dark:bg-stone-900 dark:text-stone-300"><Globe2 className="size-4" /><span className="sr-only">Voice language</span><select value={language} onChange={event => setLanguage(event.target.value)} className="max-w-20 bg-transparent outline-none">{LANGUAGES.map(([code, label]) => <option key={code} value={code}>{label}</option>)}</select></label><button type="button" onClick={logout} title="Sign out" className="grid size-9 place-items-center rounded-xl text-stone-500 hover:bg-stone-200 dark:hover:bg-stone-800"><LogOut className="size-4" /></button></div></header>

      <section className="mt-7 overflow-hidden rounded-3xl bg-stone-950 px-6 py-7 text-white shadow-card"><div className="flex items-center justify-between"><span className="rounded-full bg-white/10 px-3 py-1 text-xs font-bold uppercase tracking-wider">Voice command</span>{isListening && <span className="flex items-center gap-1 text-xs text-lime"><span className="size-2 animate-pulse rounded-full bg-lime" />Listening</span>}</div><div className="flex min-h-36 flex-col items-center justify-center text-center"><VoiceOrb isListening={isListening} disabled={!supported || working} onClick={toggle} /><p className="mt-5 text-sm font-medium text-stone-200">{!supported ? 'Voice input is not available in this browser.' : interim || (isListening ? 'Speak now…' : 'Tap to add, remove, or search')}</p></div><div className="rounded-2xl bg-white/8 px-4 py-3 text-center text-sm text-stone-100" role="status">{working ? <span className="inline-flex items-center gap-2"><LoaderCircle className="size-4 animate-spin" />Updating your list…</span> : status}</div></section>

      <form onSubmit={addManual} className="mt-4 flex gap-2"><input value={manualValue} onChange={event => setManualValue(event.target.value)} placeholder="Or type an item…" className="min-w-0 flex-1 rounded-2xl border border-stone-200 bg-white px-4 py-3 text-sm text-stone-900 outline-none placeholder:text-stone-400 focus:border-ink dark:border-stone-700 dark:bg-stone-900 dark:text-stone-100" /><button type="submit" disabled={working} className="grid size-12 place-items-center rounded-2xl bg-lime text-stone-950 transition hover:brightness-95 disabled:opacity-50" aria-label="Add typed item"><Plus /></button></form>

      {suggestions.length > 0 && <section className="mt-8"><div className="mb-3 flex items-center gap-2"><Sparkles className="size-5 text-emerald-600" /><h2 className="font-bold">A little helpful nudge</h2></div><div className="flex gap-2 overflow-x-auto pb-2">{suggestions.map(suggestion => <button type="button" key={suggestion.name} onClick={() => addSuggestion(suggestion)} disabled={working} className="min-w-36 rounded-2xl border border-stone-200 bg-white p-3 text-left shadow-sm transition hover:-translate-y-0.5 disabled:opacity-50 dark:border-stone-700 dark:bg-stone-900"><p className="font-semibold">{suggestion.name}</p><p className="mt-1 text-xs text-stone-500">{suggestion.reason}</p><span className="mt-3 inline-flex items-center gap-1 text-xs font-bold text-emerald-700"><Plus className="size-3" />Add</span></button>)}</div></section>}

      <section className="mt-8"><div className="mb-3 flex items-center justify-between"><div className="flex items-center gap-2"><ClipboardList className="size-5" /><h2 className="font-bold">Shopping list</h2><span className="rounded-full bg-mist px-2 py-0.5 text-xs font-bold text-stone-600 dark:text-stone-300">{remaining}</span></div>{items.length > 0 && <button type="button" onClick={clear} className="inline-flex items-center gap-1 text-xs font-bold text-stone-500 hover:text-red-600"><Trash2 className="size-3.5" />Clear</button>}</div>{loading ? <div className="grid min-h-36 place-items-center text-sm text-stone-500"><LoaderCircle className="mr-2 inline size-4 animate-spin" />Loading your list…</div> : items.length === 0 ? <div className="rounded-3xl border border-dashed border-stone-300 px-6 py-10 text-center dark:border-stone-700"><p className="font-semibold">Your list is delightfully empty.</p><p className="mt-1 text-sm text-stone-500">Try “Add two bottles of water”.</p></div> : <div className="space-y-5">{Object.entries(groupedItems).map(([category, categoryItems]) => <div key={category}><p className="mb-2 text-xs font-bold uppercase tracking-widest text-stone-500">{category}</p><ul className="space-y-2">{categoryItems.map(item => <ItemRow key={item.id} item={item} onUpdate={updateItem} onDelete={deleteItem} />)}</ul></div>)}</div>}{remaining > 0 && <button type="button" onClick={placeOrder} disabled={working} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-lime px-4 py-3.5 font-bold text-stone-950 transition hover:brightness-95 disabled:opacity-50"><ShoppingBag className="size-5" />Place order ({remaining})</button>}</section>

      <section className="mt-9"><div className="mb-3 flex items-center gap-2"><PackageCheck className="size-5" /><h2 className="font-bold">Order history</h2></div>{orders.length === 0 ? <p className="rounded-2xl border border-dashed border-stone-300 px-4 py-5 text-sm text-stone-500 dark:border-stone-700">Placed orders will stay here so you can track what you ordered before.</p> : <div className="space-y-3">{orders.map(order => <article key={order.id} className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm dark:border-stone-700 dark:bg-stone-900"><div className="flex items-start justify-between gap-3"><div><p className="font-bold">Order #{order.id}</p><p className="mt-0.5 text-xs text-stone-500">{new Date(order.created_at).toLocaleString()}</p></div><span className={`rounded-full px-2.5 py-1 text-xs font-bold capitalize ${statusClass(order.status)}`}>{order.status}</span></div><p className="mt-3 text-sm text-stone-600 dark:text-stone-300">{order.items.map(item => `${item.quantity % 1 ? item.quantity : Math.round(item.quantity)}${item.unit ? ` ${item.unit}` : ''} ${item.name}`).join(' · ')}</p>{order.status === 'placed' && <button type="button" onClick={() => updateOrder(order.id, 'delivered')} className="mt-3 inline-flex items-center gap-1.5 text-sm font-bold text-emerald-700 hover:text-emerald-800"><CheckCircle2 className="size-4" />Mark delivered</button>}</article>)}</div>}</section>
      <footer className="mt-10 flex items-center justify-center gap-2 text-center text-xs text-stone-500"><Volume2 className="size-3.5" />Say “Add milk”, “Remove milk”, or “Find toothpaste under 5”.</footer>
    </main>
  )
}
