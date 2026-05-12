export type BlockType =
  | 'heading'
  | 'paragraph'
  | 'list_item'
  | 'blockquote'
  | 'code'
  | 'image_caption'
  | 'table_row'
  | 'spacer'

export interface Block {
  type: BlockType
  text: string
  level?: number | null
  ordered?: boolean | null
  language?: string | null
}

export interface Document {
  id: string
  filename: string
  format: string
  word_count: number
  char_count: number
  blocks: Block[]
  warnings: string[]
}

export type FontChoice =
  | 'lexend'
  | 'inter'
  | 'atkinson'
  | 'opendyslexic'
  | 'georgia'
  | 'system'
  | 'mono'

export type ThemeChoice =
  | 'paper'      // default — warm parchment grey
  | 'fog'        // cool grey
  | 'lavender'   // soft lavender pastel
  | 'mint'       // gentle mint
  | 'cream'      // classic ivory
  | 'sepia'      // warm tan
  | 'dark'       // dark mode
  | 'light'      // pure white (option, not default)
  | 'highContrast'
  | 'lowContrast'

/**
 * App mode — drives top-level navigation.
 *
 *   welcome   → first-launch landing page (Guided / Expert / Intention).
 *   guided    → onboarding v2 wizard + simplified 3-button reading shell.
 *   expert    → full toolbar (the original UI), all knobs visible.
 *   intention → wave / quantum-entropy "intention studio" (émetteur / récepteur).
 */
export type AppMode = 'welcome' | 'guided' | 'expert' | 'intention'

/**
 * Reading profile picked by the onboarding quiz (in Guided mode).
 *
 * Each profile maps to a coherent settings preset. See PRESETS in store.ts.
 */
export type ReadingProfile = 'apaise' | 'equilibre' | 'concentre' | 'sprint' | null

/**
 * Export targets.
 *
 *   inplace : preserve the original file's format (DOCX→DOCX, PDF→PDF,
 *             PPTX→PPTX, XLSX→XLSX) with images / tables / formulas
 *             intact. Only the prefix-letter spans get bolded.
 *   html/docx/txt : rebuild from the parsed model (the original file is
 *                   never written but most non-text content is lost).
 */
export type ExportFormat = 'inplace' | 'html' | 'docx' | 'txt'

export interface Settings {
  // Bionic core
  bionicEnabled: boolean
  fixationRatio: number  // 0.2..0.8
  saccadeAdaptive: boolean
  minWordLength: number
  skipShortWords: boolean
  useColorInsteadOfBold: boolean
  prefixColor: string
  colorVowels: boolean
  vowelColor: string
  colorFirstLetter: boolean
  firstLetterColor: string

  // New attentional techniques (council additions)
  eyeAnchor: boolean            // gray dot at OVP of each word
  eyeAnchorColor: string
  phraseChunking: boolean       // small extra space every 3-5 words
  phraseChunkSize: number
  posColoring: boolean          // subtle hue on logical connectors
  posColor: string
  pulseCadence: boolean         // moving horizontal line cursor
  pulseCadenceWpm: number       // 120..400
  breathingWord: boolean        // current TTS word: weight pulse, not highlight
  autoPacing: boolean           // pomodoro-aware reading session

  // Typography
  font: FontChoice
  fontSize: number          // px
  fontWeight: number        // 300..700
  letterSpacing: number     // em
  wordSpacing: number       // em
  lineHeight: number        // unitless
  maxLineWidth: number      // ch
  paragraphSpacing: number  // em
  justify: boolean
  hyphens: boolean

  // Theme & color
  theme: ThemeChoice
  customBg: string
  customFg: string
  overlayEnabled: boolean
  overlayColor: string
  overlayOpacity: number    // 0..1

  // Visual aids
  rulerEnabled: boolean
  focusModeEnabled: boolean   // dim non-focused paragraphs
  focusModeStrength: number   // 0..1
  chunkingEnabled: boolean
  chunkSize: number           // words per chunk
  paginate: boolean

  // Modes
  rsvpEnabled: boolean
  rsvpWpm: number             // 100..1000
  rsvpChunkSize: number       // words per flash
  rsvpPauseOnPunct: boolean

  // TTS
  ttsEnabled: boolean
  ttsRate: number             // 0.5..2.0
  ttsVoice: string | null
  ttsHighlight: boolean

  // Master control (guided mode)
  quietness: 0 | 1 | 2   // 0 = tonique, 1 = équilibré, 2 = cocoon
}

export const defaultSettings: Settings = {
  bionicEnabled: true,
  fixationRatio: 0.4,            // Casutt-tuned: subtler than the literal 50%
  saccadeAdaptive: true,
  minWordLength: 4,              // skip articles + short words by default
  skipShortWords: true,
  useColorInsteadOfBold: false,
  prefixColor: '#0f172a',
  colorVowels: false,
  vowelColor: '#dc2626',
  colorFirstLetter: false,
  firstLetterColor: '#2563eb',

  eyeAnchor: true,                // Dehaene OVP
  eyeAnchorColor: '#9a958e',
  phraseChunking: false,
  phraseChunkSize: 4,
  posColoring: false,
  posColor: '#a05a1a',
  pulseCadence: false,
  pulseCadenceWpm: 220,
  breathingWord: true,
  autoPacing: false,

  font: 'lexend',
  fontSize: 19,
  fontWeight: 400,
  letterSpacing: 0.01,            // Spiekermann-tuned
  wordSpacing: 0,
  lineHeight: 1.75,
  maxLineWidth: 64,
  paragraphSpacing: 1.1,
  justify: false,
  hyphens: false,

  theme: 'paper',                 // warm parchment grey is the new default
  customBg: '#ece8e1',
  customFg: '#2a2825',
  overlayEnabled: false,
  overlayColor: '#fef3c7',
  overlayOpacity: 0.3,

  rulerEnabled: false,
  focusModeEnabled: true,         // ON by default for ADHD readers
  focusModeStrength: 0.75,        // stronger than the old 0.5
  chunkingEnabled: false,
  chunkSize: 12,
  paginate: false,

  rsvpEnabled: false,
  rsvpWpm: 350,
  rsvpChunkSize: 1,
  rsvpPauseOnPunct: true,

  ttsEnabled: false,
  ttsRate: 1.0,
  ttsVoice: null,
  ttsHighlight: true,

  quietness: 1,                   // équilibré
}

export const FONT_FAMILY: Record<FontChoice, string> = {
  lexend: '"Lexend", "Inter", system-ui, sans-serif',
  inter: '"Inter", system-ui, sans-serif',
  atkinson: '"Atkinson Hyperlegible", "Inter", system-ui, sans-serif',
  opendyslexic: '"OpenDyslexic", "Lexend", sans-serif',
  georgia: 'Georgia, "Times New Roman", serif',
  system: 'system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
  mono: '"JetBrains Mono", "Fira Code", ui-monospace, monospace',
}

export interface Theme {
  bg: string
  fg: string
  muted: string
  accent: string
  border: string
}

/**
 * All themes are calibrated to keep luminance contrast >= 7:1 (WCAG AAA)
 * while avoiding pure white / pure black extremes (Kahneman + Irlen).
 */
export const THEMES: Record<ThemeChoice, Theme> = {
  paper:        { bg: '#ece8e1', fg: '#2a2825', muted: '#6b675e', accent: '#7c5e2a', border: '#d8d2c5' },
  fog:          { bg: '#dde1e3', fg: '#262a2d', muted: '#5f6669', accent: '#3a5a6b', border: '#c8cdd0' },
  lavender:     { bg: '#e8e3ec', fg: '#2d2a33', muted: '#6b6577', accent: '#6a4f8a', border: '#d4cddb' },
  mint:         { bg: '#dfe7e1', fg: '#1f2924', muted: '#5b6962', accent: '#3a6b5a', border: '#c8d4cc' },
  cream:        { bg: '#fbfaf6', fg: '#1a1a1a', muted: '#5b5b55', accent: '#7c5e2a', border: '#e8e3d4' },
  sepia:        { bg: '#f4ecd8', fg: '#3a2e1f', muted: '#6e5e44', accent: '#a05a1a', border: '#d8c8a0' },
  dark:         { bg: '#13141a', fg: '#dcdcdc', muted: '#a0a0a0', accent: '#7dd3fc', border: '#262934' },
  light:        { bg: '#ffffff', fg: '#111827', muted: '#6b7280', accent: '#2563eb', border: '#e5e7eb' },
  highContrast: { bg: '#000000', fg: '#ffff00', muted: '#aaaa00', accent: '#00ffff', border: '#444400' },
  lowContrast:  { bg: '#2b2c33', fg: '#bcbcc6', muted: '#7c7d8a', accent: '#a3b8d8', border: '#3b3c45' },
}
