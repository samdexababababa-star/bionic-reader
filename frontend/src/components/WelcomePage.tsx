import { BookOpenText, Compass, Radio, Sliders } from 'lucide-react'
import { useApp } from '../store'
import { THEMES } from '../types'

/**
 * Landing page — first thing the user sees on launch.
 *
 * Asks: do you want a guided experience (the right thing pre-chosen for you),
 * or do you want full control (every knob exposed)?
 *
 * No file upload, no document state, no toolbar. Just two big choices.
 */
export default function WelcomePage() {
  const { setMode, onboardingDone, profile } = useApp()
  const theme = THEMES.paper

  return (
    <div
      className="h-screen w-full flex items-center justify-center px-6 font-ui"
      style={{ background: theme.bg, color: theme.fg }}
    >
      <div className="max-w-4xl w-full">
        <div className="flex items-center justify-center gap-3 mb-3">
          <BookOpenText className="w-7 h-7" style={{ color: theme.accent }} />
          <h1 className="text-2xl font-semibold tracking-tight">Bionic Reader</h1>
        </div>
        <p className="text-center mb-1 opacity-80 text-sm">
          Un lecteur pensé pour les cerveaux TDAH.
        </p>
        <p className="text-center mb-10 opacity-60 text-xs max-w-xl mx-auto">
          Lecture bionique + indicateur OVP + focus paragraphe + auto-pacing + synthèse vocale —
          tout ce que la recherche en neurosciences de la lecture suggère, combiné en un seul outil.
        </p>

        <div className="grid md:grid-cols-3 gap-4">
          <button
            onClick={() => setMode('guided')}
            className="group rounded-2xl p-6 text-left transition-all hover:shadow-md focus:outline-none focus:ring-2"
            style={{
              background: '#f5f1e8',
              border: `1px solid ${theme.border}`,
            }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: theme.accent + '22', color: theme.accent }}
              >
                <Compass className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-semibold">Mode guidé</h2>
              <span
                className="ml-auto text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={{ background: theme.accent, color: 'white' }}
              >
                Recommandé
              </span>
            </div>
            <p className="text-sm opacity-80 leading-relaxed mb-3">
              Calibration en 90 s : ASRS-6 OMS, test d&apos;attention (PVT), lecture courte.
              On en déduit ton profil et son réglage.
            </p>
            <ul className="text-xs opacity-70 space-y-1.5">
              <li>• 6 questions ASRS validées par l&apos;OMS</li>
              <li>• Test psychomoteur de vigilance (PVT)</li>
              <li>• Profil multi-dimensionnel + rationale</li>
            </ul>
            {onboardingDone && profile && (
              <p className="text-xs mt-3 italic opacity-60">
                Reprendre avec ton profil actuel : <strong>{profile}</strong>
              </p>
            )}
          </button>

          <button
            onClick={() => setMode('expert')}
            className="group rounded-2xl p-6 text-left transition-all hover:shadow-md focus:outline-none focus:ring-2"
            style={{
              background: '#eee9df',
              border: `1px solid ${theme.border}`,
            }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: theme.fg + '15', color: theme.fg }}
              >
                <Sliders className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-semibold">Mode expert</h2>
            </div>
            <p className="text-sm opacity-80 leading-relaxed mb-3">
              Toutes les options visibles, tous les sliders. Pour explorer chaque technique en détail.
            </p>
            <ul className="text-xs opacity-70 space-y-1.5">
              <li>• Ratio de fixation, saccade adaptative, POS coloring</li>
              <li>• 10 polices, 10 thèmes, overlays Irlen</li>
              <li>• RSVP, TTS synchronisé, focus paragraphe, ruler</li>
            </ul>
          </button>

          <button
            onClick={() => setMode('intention')}
            className="group rounded-2xl p-6 text-left transition-all hover:shadow-md focus:outline-none focus:ring-2"
            style={{
              background: 'linear-gradient(135deg, #efe9da 0%, #e6dfca 100%)',
              border: `1px solid ${theme.border}`,
            }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center"
                style={{ background: '#7c5e2a22', color: '#7c5e2a' }}
              >
                <Radio className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-semibold">Studio d&apos;intention</h2>
              <span
                className="ml-auto text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full"
                style={{ background: '#7c5e2a', color: 'white' }}
              >
                Nouveau
              </span>
            </div>
            <p className="text-sm opacity-80 leading-relaxed mb-3">
              Émetteur · récepteur. Une intention que tu poses, un signal tiré d&apos;entropie
              quantique réelle (ANU QRNG), un message court qui te revient.
            </p>
            <ul className="text-xs opacity-70 space-y-1.5">
              <li>• Fluctuations du vide quantique (ANU)</li>
              <li>• 22 archétypes réflexifs</li>
              <li>• Affirmation personnalisée (IA optionnelle)</li>
            </ul>
          </button>
        </div>

        <p className="text-center text-[11px] opacity-50 mt-10">
          Tu peux basculer entre les deux modes à tout moment. Tes fichiers ne sont jamais
          stockés sur le serveur.
        </p>
      </div>
    </div>
  )
}
