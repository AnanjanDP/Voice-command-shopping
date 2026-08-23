import { Check, Minus, Plus, Trash2 } from 'lucide-react'

export default function ItemRow({ item, onUpdate, onDelete }) {
  return (
    <li className="group flex items-center gap-3 rounded-2xl bg-white px-3 py-3 shadow-sm dark:bg-stone-900">
      <button type="button" onClick={() => onUpdate(item.id, { is_checked: !item.is_checked })} aria-label={`Mark ${item.name} ${item.is_checked ? 'unbought' : 'bought'}`} className={`grid size-7 shrink-0 place-items-center rounded-full border transition ${item.is_checked ? 'border-ink bg-ink text-white' : 'border-stone-300 text-transparent hover:border-ink'}`}><Check className="size-4" /></button>
      <div className="min-w-0 flex-1">
        <p className={`truncate font-semibold ${item.is_checked ? 'text-stone-400 line-through' : 'text-ink'}`}>{item.name}</p>
        <p className="text-xs text-stone-500">{item.category}{item.brand ? ` · ${item.brand}` : ''}</p>
      </div>
      <div className="flex items-center gap-1 rounded-xl bg-canvas p-1 text-sm font-semibold">
        <button type="button" onClick={() => item.quantity > 1 ? onUpdate(item.id, { quantity: item.quantity - 1 }) : onDelete(item.id)} className="grid size-7 place-items-center rounded-lg hover:bg-mist" aria-label={`Decrease ${item.name}`}><Minus className="size-3.5" /></button>
        <span className="min-w-7 text-center">{item.quantity % 1 ? item.quantity : Math.round(item.quantity)}{item.unit ? ` ${item.unit}` : ''}</span>
        <button type="button" onClick={() => onUpdate(item.id, { quantity: item.quantity + 1 })} className="grid size-7 place-items-center rounded-lg hover:bg-mist" aria-label={`Increase ${item.name}`}><Plus className="size-3.5" /></button>
      </div>
      <button type="button" onClick={() => onDelete(item.id)} className="grid size-8 place-items-center rounded-lg text-stone-400 opacity-100 transition hover:bg-red-50 hover:text-red-600 sm:opacity-0 sm:group-hover:opacity-100" aria-label={`Delete ${item.name}`}><Trash2 className="size-4" /></button>
    </li>
  )
}
