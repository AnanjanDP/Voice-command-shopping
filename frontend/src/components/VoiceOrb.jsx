import { Mic, Square } from 'lucide-react'

export default function VoiceOrb({ isListening, disabled, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={isListening ? 'Stop listening' : 'Start voice command'}
      className={`relative grid size-24 place-items-center rounded-full transition focus:outline-none focus:ring-4 focus:ring-lime/50 disabled:opacity-50 ${isListening ? 'bg-stone-950 text-white' : 'bg-lime text-stone-950 hover:scale-105'}`}
    >
      {isListening && <><span className="absolute inset-0 animate-ping rounded-full bg-lime/40" /><span className="absolute -inset-3 animate-[pulse_1.2s_ease-in-out_infinite] rounded-full border border-ink/15" /></>}
      {isListening ? <Square className="relative size-7 fill-current" /> : <Mic className="size-8" strokeWidth={2.3} />}
    </button>
  )
}
