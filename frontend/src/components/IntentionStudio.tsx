import { useState } from 'react'
import {
  ArrowLeft,
  ArrowUpRight,
  Loader2,
  Radio,
  Send,
  Sparkles,
  Waves,
} from 'lucide-react'
import { emitWave, receiveWave, type WaveSignal } from '../api'
import { useApp } from '../store'
import { THEMES } from '../types'

/**
 * Intention Studio — wave / quantum-entropy emitter & receiver.
 *
 * Honest framing:
 *
 *   1. The randomness is real quantum noise. The backend fetches bytes from
 *      ANU's Quantum Random Number Generator (vacuum fluctuations,
 *      peer-reviewed, published as Symul et al. 2011) with graceful
 *      fallback to the OS CSPRNG if the network call fails.
 *   2. The interpretation is symbolic — we pick an archetype from a
 *      hand-curated reflective set, like a tarot deck or an I Ching
 *      hexagram. The value is in the ritual of articulating an intention,
 *      not in any pretended causal effect on the world.
 *   3. An optional Mistral creative layer personalises the message to
 *      mention concrete words from the user's intention. Without the
 *      key, the archetype's plain reflection is shown.
 *
 * This screen exists for the user who wants a brief "intention check" or
 * journaling prompt before a long reading session — a calming ritual that
 * fits the ADHD-aware vibe of the rest of the app.
 */
export default function IntentionStudio() {
  const { setMode } = useApp()
  const theme = THEMES.paper

  const [tab, setTab] = useState<'emit' | 'receive'>('emit')
  const [intention, setIntention] = useState('')
  const [question, setQuestion] = useState('')
  const [signal, setSignal] = useState<WaveSignal | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleEmit() {
    if (!intention.trim()) {
      setError('Écris une intention courte avant d’émettre.')
      return
    }
    setBusy(true)
    setError(null)
    setSignal(null)
    try {
      const s = await emitWave(intention.trim())
      setSignal(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Émission impossible')
    } finally {
      setBusy(false)
    }
  }

  async function handleReceive() {
    setBusy(true)
    setError(null)
    setSignal(null)
    try {
      const s = await receiveWave(question.trim())
      setSignal(s)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Réception impossible')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div
      className="min-h-screen w-full font-ui flex flex-col"
      style={{
        background: 'radial-gradient(ellipse at top, #f5efe1 0%, #e9e2cf 60%, #ddd5be 100%)',
        color: theme.fg,
      }}
    >
      {/* Header */}
      <div className="px-6 py-4 flex items-center gap-3">
        <button
          onClick={() => setMode('welcome')}
          className="text-xs flex items-center gap-1 opacity-60 hover:opacity-100"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> accueil
        </button>
        <span className="ml-auto text-[10px] uppercase tracking-wider opacity-50">
          Intention Studio
        </span>
      </div>

      <div className="flex-1 flex items-start justify-center px-6 pb-12 pt-2">
        <div className="w-full max-w-2xl">
          {/* Header */}
          <div className="flex items-center justify-center gap-3 mb-2">
            <Waves className="w-7 h-7" style={{ color: '#7c5e2a' }} />
            <h1 className="text-2xl font-semibold tracking-tight">Émetteur · Récepteur</h1>
          </div>
          <p className="text-center text-xs opacity-65 max-w-md mx-auto mb-7 leading-relaxed">
            Entropie quantique réelle (fluctuations du vide, laboratoire ANU) +
            22 archétypes réflexifs. Pas de divination — un mini-rituel pour
            articuler une intention et recevoir un mot précis.
          </p>

          {/* Tabs */}
          <div className="flex gap-1 mb-5 p-1 rounded-xl" style={{ background: '#ece5d2' }}>
            <TabButton
              active={tab === 'emit'}
              onClick={() => {
                setTab('emit')
                setSignal(null)
                setError(null)
              }}
              icon={<Send className="w-3.5 h-3.5" />}
              label="Émettre"
            />
            <TabButton
              active={tab === 'receive'}
              onClick={() => {
                setTab('receive')
                setSignal(null)
                setError(null)
              }}
              icon={<Radio className="w-3.5 h-3.5" />}
              label="Recevoir"
            />
          </div>

          {/* Input area */}
          {tab === 'emit' && (
            <div className="mb-5">
              <label className="block text-xs uppercase tracking-wider opacity-60 mb-2">
                Ton intention, en une ou deux phrases
              </label>
              <textarea
                value={intention}
                onChange={(e) => setIntention(e.target.value)}
                placeholder="Aujourd'hui, je veux retrouver de la clarté sur mon projet."
                rows={3}
                className="w-full px-4 py-3 rounded-xl text-sm leading-relaxed focus:outline-none focus:ring-2 resize-none"
                style={{
                  background: '#fefcf6',
                  border: `1px solid ${theme.border}`,
                  color: theme.fg,
                }}
                disabled={busy}
              />
              <button
                onClick={handleEmit}
                disabled={busy || !intention.trim()}
                className="mt-3 px-5 py-3 rounded-xl text-sm font-medium flex items-center gap-2 transition-all hover:translate-y-[-1px] disabled:opacity-50"
                style={{
                  background: '#7c5e2a',
                  color: 'white',
                  minHeight: 44,
                }}
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Émettre l’onde
              </button>
            </div>
          )}

          {tab === 'receive' && (
            <div className="mb-5">
              <label className="block text-xs uppercase tracking-wider opacity-60 mb-2">
                Question ouverte (facultatif)
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Sur quoi devrais-je porter mon attention en ce moment ?"
                rows={3}
                className="w-full px-4 py-3 rounded-xl text-sm leading-relaxed focus:outline-none focus:ring-2 resize-none"
                style={{
                  background: '#fefcf6',
                  border: `1px solid ${theme.border}`,
                  color: theme.fg,
                }}
                disabled={busy}
              />
              <button
                onClick={handleReceive}
                disabled={busy}
                className="mt-3 px-5 py-3 rounded-xl text-sm font-medium flex items-center gap-2 transition-all hover:translate-y-[-1px] disabled:opacity-50"
                style={{
                  background: '#7c5e2a',
                  color: 'white',
                  minHeight: 44,
                }}
              >
                {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Radio className="w-4 h-4" />}
                Recevoir un signal
              </button>
            </div>
          )}

          {error && (
            <p className="text-sm mb-4" style={{ color: '#a52a2a' }}>
              {error}
            </p>
          )}

          {/* Signal output */}
          {signal && <SignalCard signal={signal} />}

          {/* Footer disclaimer */}
          <details className="mt-10 text-xs opacity-60 cursor-pointer">
            <summary className="font-medium opacity-80">
              D’où vient le « caractère quantique » de cet outil ?
            </summary>
            <p className="mt-3 leading-relaxed">
              Les bits aléatoires utilisés ici sont fournis par l’API publique du
              Quantum Random Number Generator de l’ANU (Australian National
              University), qui mesure les fluctuations du vide quantique via
              interférométrie cohérente (Symul, Assad & Lam, <i>Appl. Phys. Lett.</i> 2011).
              Si la connexion échoue, on retombe sur le CSPRNG du noyau (toujours
              cryptographiquement sain).
            </p>
            <p className="mt-2 leading-relaxed">
              Le système ne prétend <strong>pas</strong> influencer la réalité ; il offre
              un cadre rituel rigoureux pour t’aider à articuler une intention ou à
              porter ton attention sur un aspect choisi par hasard, comme tu le
              ferais avec un I Ching ou un dé.
            </p>
          </details>
        </div>
      </div>
    </div>
  )
}

function TabButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className="flex-1 px-4 py-2.5 rounded-lg text-sm flex items-center justify-center gap-2 transition-all"
      style={{
        background: active ? '#fefcf6' : 'transparent',
        boxShadow: active ? '0 1px 4px rgba(0,0,0,0.06)' : 'none',
        color: active ? '#7c5e2a' : '#5b5b55',
        fontWeight: active ? 600 : 500,
      }}
    >
      {icon}
      {label}
    </button>
  )
}

function SignalCard({ signal }: { signal: WaveSignal }) {
  return (
    <div
      className="rounded-2xl p-6 relative overflow-hidden"
      style={{
        background: 'linear-gradient(135deg, #fefcf6 0%, #f7f0dd 100%)',
        border: '1px solid #d8c8a0',
      }}
    >
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="w-4 h-4" style={{ color: '#7c5e2a' }} />
        <span className="text-[10px] uppercase tracking-wider opacity-60">
          Archétype tiré
        </span>
        <span className="ml-auto text-[10px] tabular-nums opacity-50">
          #{signal.archetype.code} · {signal.archetype.tone}
        </span>
      </div>
      <h3 className="text-2xl font-semibold mb-3">{signal.archetype.name}</h3>
      <p className="text-sm leading-relaxed mb-5">{signal.message}</p>

      <div className="flex items-center gap-3 text-[11px] opacity-65 flex-wrap">
        <span className="flex items-center gap-1">
          <ArrowUpRight className="w-3 h-3" />
          source :{' '}
          <span className="font-medium">
            {signal.source === 'anu_qrng' ? 'ANU QRNG (quantique)' : 'CSPRNG kernel (fallback)'}
          </span>
        </span>
        <span className="opacity-50">·</span>
        <span>
          signature : <span className="font-mono">{signal.signature}</span>
        </span>
        {signal.used_llm && (
          <>
            <span className="opacity-50">·</span>
            <span>texte affiné par IA (Mistral)</span>
          </>
        )}
      </div>
    </div>
  )
}
