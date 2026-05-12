import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  ArrowRight,
  Brain,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Compass,
  Loader2,
  SkipForward,
  Sparkles,
  Target,
  Timer,
} from 'lucide-react'
import { useApp, PROFILE_LABELS } from '../store'
import { THEMES, type ReadingProfile } from '../types'
import {
  calibrateProfile,
  type ASRSResponse,
  type CalibrationResponse,
  type PVTResult,
  type ReadingTestResult,
} from '../api'

/**
 * Guided onboarding v2 — five steps:
 *
 *   1. Intro (set expectations, allow skip)
 *   2. ASRS-v1.1 Part A — 6 Likert questions (WHO short ADHD screener)
 *   3. PVT — 16-trial Psychomotor Vigilance Task
 *   4. Reading test — 60-word paragraph, measure WPM
 *   5. Result — multi-dimensional profile + apply
 *
 * Each step except step 1 and 5 is skippable (`Tout passer` available from
 * step 1, individual `Passer cette étape` on each test). Skipping reduces
 * confidence in the resulting profile but never blocks completion.
 *
 * UI design follows the COUNCIL.md guidance:
 *   - max 5 cognitive units on screen (Barkley working memory)
 *   - large tap targets (Fitt's law) — buttons ≥ 44 px tall
 *   - calm parchment palette by default
 *   - progress always visible (Csikszentmihalyi)
 *   - no jargon ("Souvent" rather than "Likert level 3")
 */

type Step = 'intro' | 'asrs' | 'pvt' | 'reading' | 'result'

type LikertChoice = { label: string; value: 0 | 1 | 2 | 3 | 4 }

const LIKERT: LikertChoice[] = [
  { label: 'Jamais', value: 0 },
  { label: 'Rarement', value: 1 },
  { label: 'Parfois', value: 2 },
  { label: 'Souvent', value: 3 },
  { label: 'Très souvent', value: 4 },
]

/**
 * ASRS-v1.1 Part A (Kessler 2005, WHO short screener) — 6 items.
 * Items 1-4 capture inattention; items 5-6 capture hyperactivity/impulsivity.
 */
const ASRS_QUESTIONS: { id: number; q: string }[] = [
  {
    id: 1,
    q: "À quelle fréquence as-tu du mal à finir les derniers détails d'un projet, une fois que les parties les plus stimulantes sont faites ?",
  },
  {
    id: 2,
    q: "À quelle fréquence as-tu du mal à mettre les choses en ordre quand tu dois faire une tâche qui demande de l'organisation ?",
  },
  {
    id: 3,
    q: "À quelle fréquence as-tu des problèmes pour te souvenir de rendez-vous ou d'obligations ?",
  },
  {
    id: 4,
    q: "Quand tu as une tâche qui demande beaucoup de réflexion, à quelle fréquence évites-tu de commencer ou la remets-tu à plus tard ?",
  },
  {
    id: 5,
    q: 'À quelle fréquence bouges-tu ou as-tu un membre qui s’agite quand tu es assis(e) longtemps ?',
  },
  {
    id: 6,
    q: "À quelle fréquence te sens-tu trop actif/active et poussé(e) à faire des choses, comme si tu étais propulsé(e) par un moteur ?",
  },
]

const PVT_TRIALS = 16
const PVT_MIN_DELAY_MS = 2000
const PVT_MAX_DELAY_MS = 6000

const READING_SAMPLE = `Le cerveau humain ne lit pas en glissant : il fait de courts arrêts appelés fixations,
puis saute d'un point à l'autre par saccades rapides. Une fixation dure entre 200 et 250
millisecondes selon le mot, et la fovéa ne perçoit nettement que sept à huit lettres autour
du point regardé. C'est pour cela qu'une mise en forme typographique pensée — premières
lettres en gras, espacement légèrement plus large, fond doux — peut sembler aider l'œil
à atterrir au bon endroit, surtout chez les lecteurs qui décrochent vite ou qui doivent
relire plusieurs fois la même phrase pour la retenir.`

const READING_WORDS = READING_SAMPLE.trim().split(/\s+/).filter(Boolean).length

export default function OnboardingWizard({ onDone }: { onDone: () => void }) {
  const { applyProfile, setOnboardingDone } = useApp()
  const theme = THEMES.paper

  const [step, setStep] = useState<Step>('intro')
  const [asrsAnswers, setAsrsAnswers] = useState<Record<number, number>>({})
  const [asrsIndex, setAsrsIndex] = useState(0)
  const [pvtResult, setPvtResult] = useState<PVTResult | null>(null)
  const [readingResult, setReadingResult] = useState<ReadingTestResult | null>(null)
  const [skipAll, setSkipAll] = useState(false)
  const [calibrating, setCalibrating] = useState(false)
  const [calibrated, setCalibrated] = useState<CalibrationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const stepIndex = useMemo(
    () => ({ intro: 0, asrs: 1, pvt: 2, reading: 3, result: 4 }[step]),
    [step],
  )

  function goNext(from: Step) {
    if (from === 'intro') setStep('asrs')
    else if (from === 'asrs') setStep('pvt')
    else if (from === 'pvt') setStep('reading')
    else if (from === 'reading') setStep('result')
  }

  const runCalibration = useCallback(async () => {
    setCalibrating(true)
    setError(null)
    try {
      const asrs: ASRSResponse[] = Object.entries(asrsAnswers).map(([id, v]) => ({
        question_id: Number(id),
        value: v,
      }))
      const res = await calibrateProfile({
        asrs,
        pvt: pvtResult,
        reading: readingResult,
      })
      setCalibrated(res)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Calibration impossible')
    } finally {
      setCalibrating(false)
    }
  }, [asrsAnswers, pvtResult, readingResult])

  // When we arrive on the result screen, kick off calibration once.
  useEffect(() => {
    if (step === 'result' && !calibrated && !calibrating) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void runCalibration()
    }
  }, [step, calibrated, calibrating, runCalibration])

  function applyAndContinue() {
    if (!calibrated) return
    applyProfile(calibrated.profile as ReadingProfile)
    setOnboardingDone(true)
    onDone()
  }

  return (
    <div
      className="h-screen w-full flex flex-col items-center justify-center px-4 font-ui overflow-y-auto"
      style={{ background: theme.bg, color: theme.fg }}
    >
      <div className="w-full max-w-2xl py-8">
        {/* Header */}
        <div className="flex items-center gap-2 mb-5">
          <Compass className="w-5 h-5" style={{ color: theme.accent }} />
          <span className="text-sm font-medium">Calibration · profil de lecture</span>
          <span className="ml-auto text-xs opacity-60 tabular-nums">
            étape {stepIndex + 1} / 5
          </span>
        </div>

        {/* Progress bar */}
        <ProgressDots current={stepIndex} theme={theme} />

        {step === 'intro' && (
          <IntroStep
            theme={theme}
            onStart={() => goNext('intro')}
            onSkipAll={() => {
              setSkipAll(true)
              setStep('result')
            }}
          />
        )}

        {step === 'asrs' && (
          <ASRSStep
            theme={theme}
            index={asrsIndex}
            answers={asrsAnswers}
            onAnswer={(qid, v) => {
              setAsrsAnswers((prev) => ({ ...prev, [qid]: v }))
              if (asrsIndex + 1 < ASRS_QUESTIONS.length) {
                setAsrsIndex(asrsIndex + 1)
              } else {
                goNext('asrs')
              }
            }}
            onPrev={() => {
              if (asrsIndex > 0) setAsrsIndex(asrsIndex - 1)
              else setStep('intro')
            }}
            onSkip={() => goNext('asrs')}
          />
        )}

        {step === 'pvt' && (
          <PVTStep
            theme={theme}
            onDone={(result) => {
              setPvtResult(result)
              goNext('pvt')
            }}
            onSkip={() => goNext('pvt')}
          />
        )}

        {step === 'reading' && (
          <ReadingStep
            theme={theme}
            onDone={(result) => {
              setReadingResult(result)
              goNext('reading')
            }}
            onSkip={() => goNext('reading')}
          />
        )}

        {step === 'result' && (
          <ResultStep
            theme={theme}
            calibrating={calibrating}
            calibrated={calibrated}
            skipAll={skipAll}
            error={error}
            onRetry={() => void runCalibration()}
            onApply={applyAndContinue}
            onRestart={() => {
              setStep('intro')
              setAsrsAnswers({})
              setAsrsIndex(0)
              setPvtResult(null)
              setReadingResult(null)
              setCalibrated(null)
              setSkipAll(false)
              setError(null)
            }}
          />
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 1 — Intro
// ---------------------------------------------------------------------------

function IntroStep({
  theme,
  onStart,
  onSkipAll,
}: {
  theme: (typeof THEMES)[keyof typeof THEMES]
  onStart: () => void
  onSkipAll: () => void
}) {
  return (
    <div className="mt-2">
      <h2 className="text-2xl md:text-3xl font-semibold leading-tight mb-3">
        Trouvons ton réglage idéal en 90 secondes.
      </h2>
      <p className="opacity-80 text-sm leading-relaxed mb-6 max-w-xl">
        Trois micro-tests scientifiques, sans jugement : un questionnaire validé par l'OMS,
        une mesure d'attention soutenue (clics rapides), et une lecture courte chronométrée.
        À la fin, tu reçois un profil personnalisé et une explication claire de pourquoi
        celui-ci te correspond.
      </p>

      <div className="grid sm:grid-cols-3 gap-3 mb-7">
        <StepHint icon={<Brain className="w-4 h-4" />} title="6 questions ASRS" desc="Test court validé OMS · 30 s" />
        <StepHint icon={<Target className="w-4 h-4" />} title="Test d'attention" desc="16 clics rapides · 30 s" />
        <StepHint icon={<Timer className="w-4 h-4" />} title="Lecture courte" desc="60 mots · 20-30 s" />
      </div>

      <div className="flex gap-3 flex-wrap">
        <BigButton primary theme={theme} onClick={onStart}>
          Commencer <ArrowRight className="w-4 h-4" />
        </BigButton>
        <BigButton theme={theme} onClick={onSkipAll}>
          <SkipForward className="w-4 h-4" /> Tout passer
        </BigButton>
      </div>

      <p className="text-xs opacity-50 mt-6 max-w-xl">
        Aucune donnée n'est envoyée à un tiers. Tes réponses servent uniquement à choisir
        l'un des 4 presets de lecture (Apaisé · Équilibré · Concentré · Sprint).
      </p>
    </div>
  )
}

function StepHint({ icon, title, desc }: { icon: React.ReactNode; title: string; desc: string }) {
  return (
    <div className="rounded-xl p-3" style={{ background: '#f3eee3', border: '1px solid #d8d2c5' }}>
      <div className="flex items-center gap-2 mb-1">
        <span className="opacity-80">{icon}</span>
        <span className="text-sm font-medium">{title}</span>
      </div>
      <div className="text-xs opacity-65">{desc}</div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 2 — ASRS-v1.1
// ---------------------------------------------------------------------------

function ASRSStep({
  theme,
  index,
  answers,
  onAnswer,
  onPrev,
  onSkip,
}: {
  theme: (typeof THEMES)[keyof typeof THEMES]
  index: number
  answers: Record<number, number>
  onAnswer: (qid: number, v: number) => void
  onPrev: () => void
  onSkip: () => void
}) {
  const q = ASRS_QUESTIONS[index]
  return (
    <div className="mt-2">
      <div className="flex items-center gap-2 mb-2">
        <Brain className="w-4 h-4" style={{ color: theme.accent }} />
        <span className="text-xs opacity-60 tabular-nums">
          question {index + 1} / {ASRS_QUESTIONS.length}
        </span>
      </div>
      <h2 className="text-xl md:text-2xl font-semibold leading-snug mb-5">{q.q}</h2>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2.5 mb-5">
        {LIKERT.map((c) => {
          const selected = answers[q.id] === c.value
          return (
            <button
              key={c.value}
              onClick={() => onAnswer(q.id, c.value)}
              className="px-4 py-3.5 rounded-xl text-sm font-medium transition-all focus:outline-none focus:ring-2"
              style={{
                background: selected ? theme.accent : '#f3eee3',
                color: selected ? 'white' : theme.fg,
                border: `1px solid ${selected ? theme.accent : theme.border}`,
                minHeight: 48,
              }}
            >
              {c.label}
            </button>
          )
        })}
      </div>

      <div className="flex items-center gap-3 text-sm">
        <button
          onClick={onPrev}
          className="opacity-60 hover:opacity-100 px-2 py-1"
        >
          ← précédent
        </button>
        <button
          onClick={onSkip}
          className="ml-auto text-xs opacity-60 hover:opacity-100 flex items-center gap-1"
        >
          <SkipForward className="w-3.5 h-3.5" /> passer ce test
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 3 — PVT (Psychomotor Vigilance Task)
// ---------------------------------------------------------------------------

type PVTState = 'waiting' | 'idle' | 'stimulus' | 'done'

function PVTStep({
  theme,
  onDone,
  onSkip,
}: {
  theme: (typeof THEMES)[keyof typeof THEMES]
  onDone: (r: PVTResult) => void
  onSkip: () => void
}) {
  const [state, setState] = useState<PVTState>('waiting')
  const [trial, setTrial] = useState(0)
  const [rts, setRts] = useState<number[]>([])
  const [falseStarts, setFalseStarts] = useState(0)
  const stimulusStartRef = useRef<number | null>(null)
  const timerRef = useRef<number | null>(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  function scheduleStimulus() {
    setState('idle')
    const delay = PVT_MIN_DELAY_MS + Math.random() * (PVT_MAX_DELAY_MS - PVT_MIN_DELAY_MS)
    timerRef.current = window.setTimeout(() => {
      stimulusStartRef.current = performance.now()
      setState('stimulus')
    }, delay)
  }

  useEffect(() => {
    return () => clearTimer()
  }, [clearTimer])

  function handleClick() {
    if (state === 'waiting') {
      // First click — start the task.
      setTrial(0)
      setRts([])
      setFalseStarts(0)
      scheduleStimulus()
      return
    }
    if (state === 'idle') {
      // False start.
      clearTimer()
      setFalseStarts((n) => n + 1)
      scheduleStimulus()
      return
    }
    if (state === 'stimulus' && stimulusStartRef.current) {
      const rt = performance.now() - stimulusStartRef.current
      const nextRts = [...rts, rt]
      setRts(nextRts)
      const nextTrial = trial + 1
      if (nextTrial >= PVT_TRIALS) {
        const sorted = [...nextRts].sort((a, b) => a - b)
        const median = sorted[Math.floor(sorted.length / 2)]
        const mean = nextRts.reduce((a, b) => a + b, 0) / nextRts.length
        const lapses = nextRts.filter((r) => r > 500).length
        setState('done')
        onDone({
          median_rt_ms: median,
          mean_rt_ms: mean,
          lapses,
          false_starts: falseStarts,
          trials: nextTrial,
        })
        return
      }
      setTrial(nextTrial)
      scheduleStimulus()
    }
  }

  const progress = (trial / PVT_TRIALS) * 100

  let body: React.ReactNode
  if (state === 'waiting') {
    body = (
      <div className="text-center">
        <h3 className="text-xl font-semibold mb-2">Test d'attention soutenue</h3>
        <p className="text-sm opacity-75 mb-5 max-w-md mx-auto leading-relaxed">
          Quand le cercle se remplit, clique aussi vite que possible. Ne clique pas avant —
          on mesure aussi les faux départs. {PVT_TRIALS} essais, environ 30 secondes.
        </p>
        <BigButton primary theme={theme} onClick={handleClick}>
          Commencer le test <ArrowRight className="w-4 h-4" />
        </BigButton>
      </div>
    )
  } else if (state === 'done') {
    body = (
      <div className="text-center text-sm opacity-80">
        <CheckCircle2 className="w-8 h-8 mx-auto mb-2" style={{ color: theme.accent }} />
        Test terminé.
      </div>
    )
  } else {
    body = (
      <div className="text-center">
        <p className="text-xs opacity-60 mb-3 tabular-nums">
          essai {trial + 1} / {PVT_TRIALS}
        </p>
        <button
          onClick={handleClick}
          className="w-full max-w-md aspect-[2/1] rounded-2xl flex items-center justify-center transition-all"
          style={{
            background: state === 'stimulus' ? theme.accent : '#f3eee3',
            border: `1px solid ${state === 'stimulus' ? theme.accent : theme.border}`,
            color: state === 'stimulus' ? 'white' : theme.fg,
            cursor: 'pointer',
          }}
        >
          {state === 'stimulus' ? (
            <CircleDot className="w-12 h-12" />
          ) : (
            <span className="text-sm opacity-50">attends le signal…</span>
          )}
        </button>
        <p className="text-xs opacity-50 mt-3">
          {falseStarts > 0 && `faux départs : ${falseStarts}`}
        </p>
      </div>
    )
  }

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2 mb-3">
        <Target className="w-4 h-4" style={{ color: theme.accent }} />
        <span className="text-xs opacity-60">Tâche de vigilance psychomotrice (PVT)</span>
      </div>
      <div
        className="h-[3px] rounded-full mb-6"
        style={{ background: theme.border }}
      >
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${progress}%`, background: theme.accent }}
        />
      </div>

      <div className="mb-5 min-h-[260px] flex items-center justify-center">
        {body}
      </div>

      <div className="flex items-center text-sm">
        <button onClick={onSkip} className="ml-auto text-xs opacity-60 hover:opacity-100 flex items-center gap-1">
          <SkipForward className="w-3.5 h-3.5" /> passer ce test
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 4 — Reading speed test
// ---------------------------------------------------------------------------

type ReadingState = 'waiting' | 'reading' | 'difficulty' | 'done'

function ReadingStep({
  theme,
  onDone,
  onSkip,
}: {
  theme: (typeof THEMES)[keyof typeof THEMES]
  onDone: (r: ReadingTestResult) => void
  onSkip: () => void
}) {
  const [state, setState] = useState<ReadingState>('waiting')
  const startRef = useRef<number | null>(null)
  const elapsedRef = useRef<number>(0)
  const [difficulty, setDifficulty] = useState<number | null>(null)

  function start() {
    startRef.current = performance.now()
    setState('reading')
  }

  function done() {
    if (startRef.current === null) return
    elapsedRef.current = performance.now() - startRef.current
    setState('difficulty')
  }

  function submitDifficulty(d: number) {
    setDifficulty(d)
    setState('done')
    onDone({
      words: READING_WORDS,
      elapsed_ms: elapsedRef.current,
      self_reported_difficulty: d,
    })
  }

  return (
    <div className="mt-2">
      <div className="flex items-center gap-2 mb-3">
        <Timer className="w-4 h-4" style={{ color: theme.accent }} />
        <span className="text-xs opacity-60">Lecture courte chronométrée</span>
      </div>

      {state === 'waiting' && (
        <div>
          <p className="text-sm opacity-80 mb-5 leading-relaxed max-w-xl">
            Lis le paragraphe ci-dessous à ton rythme naturel. Dès que tu as fini, clique
            sur « J'ai fini ». On mesure ta vitesse de lecture confortable, pas la rapidité maximale.
          </p>
          <div
            className="rounded-xl p-5 mb-5 text-sm leading-relaxed select-none"
            style={{ background: '#f3eee3', border: `1px solid ${theme.border}`, filter: 'blur(3px)', userSelect: 'none' }}
          >
            {READING_SAMPLE}
          </div>
          <BigButton primary theme={theme} onClick={start}>
            Démarrer la lecture <ArrowRight className="w-4 h-4" />
          </BigButton>
        </div>
      )}

      {state === 'reading' && (
        <div>
          <div
            className="rounded-xl p-5 mb-5 leading-relaxed"
            style={{ background: '#f3eee3', border: `1px solid ${theme.border}`, fontSize: 17 }}
          >
            {READING_SAMPLE}
          </div>
          <BigButton primary theme={theme} onClick={done}>
            <CheckCircle2 className="w-4 h-4" /> J'ai fini
          </BigButton>
        </div>
      )}

      {state === 'difficulty' && (
        <div>
          <h3 className="text-lg font-semibold mb-3">Sur une échelle, c'était…</h3>
          <div className="grid grid-cols-5 gap-2 mb-4">
            {[
              { v: 0, l: 'Très facile' },
              { v: 1, l: 'Facile' },
              { v: 2, l: 'Moyen' },
              { v: 3, l: 'Difficile' },
              { v: 4, l: 'Très difficile' },
            ].map((c) => (
              <button
                key={c.v}
                onClick={() => submitDifficulty(c.v)}
                className="px-3 py-3 rounded-xl text-sm transition-all"
                style={{
                  background: '#f3eee3',
                  border: `1px solid ${theme.border}`,
                  minHeight: 56,
                }}
              >
                {c.l}
              </button>
            ))}
          </div>
        </div>
      )}

      {state === 'done' && (
        <div className="text-center text-sm opacity-80">
          <CheckCircle2 className="w-8 h-8 mx-auto mb-2" style={{ color: theme.accent }} />
          Lecture enregistrée
          {difficulty !== null && (
            <span className="block text-xs opacity-60 mt-1">
              difficulté ressentie : {difficulty}/4
            </span>
          )}
        </div>
      )}

      <div className="flex items-center text-sm mt-4">
        <button onClick={onSkip} className="ml-auto text-xs opacity-60 hover:opacity-100 flex items-center gap-1">
          <SkipForward className="w-3.5 h-3.5" /> passer ce test
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Step 5 — Result + Apply
// ---------------------------------------------------------------------------

function ResultStep({
  theme,
  calibrating,
  calibrated,
  skipAll,
  error,
  onRetry,
  onApply,
  onRestart,
}: {
  theme: (typeof THEMES)[keyof typeof THEMES]
  calibrating: boolean
  calibrated: CalibrationResponse | null
  skipAll: boolean
  error: string | null
  onRetry: () => void
  onApply: () => void
  onRestart: () => void
}) {
  if (calibrating) {
    return (
      <div className="mt-10 text-center">
        <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" style={{ color: theme.accent }} />
        <p className="text-sm opacity-75">Analyse de tes réponses…</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mt-6">
        <p className="text-sm" style={{ color: '#a52a2a' }}>
          {error}
        </p>
        <div className="flex gap-3 mt-4">
          <BigButton primary theme={theme} onClick={onRetry}>
            Réessayer
          </BigButton>
        </div>
      </div>
    )
  }

  if (!calibrated) return null

  const profileLabel = PROFILE_LABELS[calibrated.profile]

  return (
    <div className="mt-2">
      {skipAll && (
        <p className="text-xs italic opacity-60 mb-2">
          Tu as choisi de tout passer — on te propose un profil par défaut (Équilibré).
          Tu peux relancer la calibration plus tard.
        </p>
      )}

      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-4 h-4" style={{ color: theme.accent }} />
        <span className="text-xs uppercase tracking-wider opacity-60">Profil recommandé</span>
      </div>

      <h2 className="text-2xl md:text-3xl font-semibold mb-2">{profileLabel.name}</h2>
      <p className="text-sm opacity-80 mb-6 leading-relaxed">{profileLabel.tagline}</p>

      <div
        className="rounded-xl p-4 mb-6"
        style={{ background: '#f3eee3', border: `1px solid ${theme.border}` }}
      >
        <p className="text-sm leading-relaxed">
          <strong className="font-medium">Pourquoi : </strong>
          {calibrated.rationale}
        </p>
      </div>

      <DimensionalBars dimensions={calibrated.dimensions} theme={theme} />
      <AffinityBars affinities={calibrated.affinities} profile={calibrated.profile} theme={theme} />

      <p className="text-xs opacity-60 mb-6 tabular-nums">
        Confiance d'estimation : {Math.round(calibrated.confidence * 100)} %
      </p>

      <div className="flex gap-3 flex-wrap">
        <BigButton primary theme={theme} onClick={onApply}>
          Appliquer et lire <ChevronRight className="w-4 h-4" />
        </BigButton>
        <BigButton theme={theme} onClick={onRestart}>
          Refaire la calibration
        </BigButton>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Atoms
// ---------------------------------------------------------------------------

function ProgressDots({
  current,
  theme,
}: {
  current: number
  theme: (typeof THEMES)[keyof typeof THEMES]
}) {
  return (
    <div className="flex gap-1.5 mb-10">
      {[0, 1, 2, 3, 4].map((i) => (
        <div
          key={i}
          className="flex-1 h-[3px] rounded-full transition-all"
          style={{
            background: i <= current ? theme.accent : theme.border,
          }}
        />
      ))}
    </div>
  )
}

function BigButton({
  children,
  onClick,
  primary,
  theme,
}: {
  children: React.ReactNode
  onClick: () => void
  primary?: boolean
  theme: (typeof THEMES)[keyof typeof THEMES]
}) {
  return (
    <button
      onClick={onClick}
      className="px-5 py-3 rounded-xl text-sm font-medium flex items-center gap-2 transition-all hover:translate-y-[-1px] focus:outline-none focus:ring-2"
      style={{
        background: primary ? theme.accent : 'transparent',
        color: primary ? 'white' : theme.fg,
        border: primary ? `1px solid ${theme.accent}` : `1px solid ${theme.border}`,
        minHeight: 44,
      }}
    >
      {children}
    </button>
  )
}

const DIMENSION_LABELS: { key: keyof CalibrationResponse['dimensions']; label: string }[] = [
  { key: 'inattention', label: 'Inattention' },
  { key: 'hyperactivity_impulsivity', label: 'Impulsivité' },
  { key: 'distraction_sensitivity', label: 'Sensibilité aux distractions' },
  { key: 'working_memory', label: 'Mémoire de travail' },
  { key: 'processing_speed', label: 'Vitesse de traitement' },
]

function DimensionalBars({
  dimensions,
  theme,
}: {
  dimensions: CalibrationResponse['dimensions']
  theme: (typeof THEMES)[keyof typeof THEMES]
}) {
  return (
    <div className="mb-6">
      <h3 className="text-xs font-medium uppercase tracking-wider opacity-60 mb-3">
        Dimensions détectées
      </h3>
      <div className="space-y-2.5">
        {DIMENSION_LABELS.map(({ key, label }) => {
          const v = dimensions[key]
          return (
            <div key={key} className="flex items-center gap-3 text-xs">
              <span className="opacity-75 w-44 shrink-0">{label}</span>
              <div className="flex-1 h-1.5 rounded-full" style={{ background: theme.border }}>
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.round(v * 100)}%`, background: theme.accent }}
                />
              </div>
              <span className="tabular-nums opacity-60 w-10 text-right">
                {Math.round(v * 100)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function AffinityBars({
  affinities,
  profile,
  theme,
}: {
  affinities: CalibrationResponse['affinities']
  profile: CalibrationResponse['profile']
  theme: (typeof THEMES)[keyof typeof THEMES]
}) {
  const entries = (
    ['apaise', 'equilibre', 'concentre', 'sprint'] as const
  ).map((k) => ({ k, v: affinities[k] }))

  return (
    <div className="mb-6">
      <h3 className="text-xs font-medium uppercase tracking-wider opacity-60 mb-3">
        Affinités preset
      </h3>
      <div className="grid grid-cols-2 gap-2.5">
        {entries.map(({ k, v }) => (
          <div key={k} className="flex items-center gap-2 text-xs">
            <span className="w-20 opacity-75">{PROFILE_LABELS[k].name}</span>
            <div className="flex-1 h-1.5 rounded-full" style={{ background: theme.border }}>
              <div
                className="h-full rounded-full"
                style={{
                  width: `${Math.round(v * 100)}%`,
                  background: k === profile ? theme.accent : theme.muted,
                }}
              />
            </div>
            <span className="tabular-nums opacity-60 w-10 text-right">
              {Math.round(v * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
