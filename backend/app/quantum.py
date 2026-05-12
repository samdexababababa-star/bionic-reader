"""Wave / quantum-entropy intention studio (the "Émetteur / Récepteur").

This module is the engine behind the optional **Intention Studio** that
appears on the welcome screen. The conceit is honest:

1. **The randomness is real quantum noise.** We fetch raw bytes from
   ANU's online Quantum Random Number Generator (free, public,
   peer-reviewed). The numbers come from measuring vacuum fluctuations
   in the QRNG lab at the Australian National University (Symul et al.,
   *Appl. Phys. Lett.* 2011). If the network call fails for any reason
   we fall back to the OS CSPRNG (`secrets.token_bytes`), which is itself
   collected from kernel-level entropy sources — still genuine
   unpredictability, just not "quantum-grade".

2. **The interpretation is symbolic.** We do NOT claim the entropy
   reflects the user's intention — that would be unscientific. What we
   *do* do is treat the entropy as a fair coin / dice roll that picks
   one of N pre-curated symbolic archetypes, the same way a user might
   shuffle a tarot deck or pull an I-Ching hexagram. The value to the
   user is the **ritual** of journaling their intention, not a magical
   "vibe match".

3. **The optional LLM layer** (Mistral) re-renders the chosen archetype
   as a personalised affirmation that incorporates words from the user's
   intention. This makes the output feel resonant without making any
   pseudo-scientific claim. If `MISTRAL_API_KEY` is unset, we serve the
   archetype text directly with light templating.

This is closer to a meditation / journaling tool than a divination tool,
which is the only honest framing.

References for the physics layer (kept in `RESEARCH_QUANTUM.md`):

- Symul T, Assad SM, Lam PK. *Real time demonstration of high bitrate
  quantum random number generation with coherent laser light*.
  Appl. Phys. Lett. 98, 231103 (2011).
- ANU QRNG public API:
  https://qrng.anu.edu.au/contact/api-documentation/
- Bell J. *On the Einstein-Podolsky-Rosen paradox*. Physics 1, 195 (1964).
- Aspect A, Grangier P, Roger G. *Experimental tests of Bell's
  inequalities using time-varying analyzers*. PRL 49, 1804 (1982).
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import secrets
import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Entropy sources
# ---------------------------------------------------------------------------

ANU_URL = "https://qrng.anu.edu.au/API/jsonI.php"
ANU_TIMEOUT_S = 4.0


class EntropyResult(BaseModel):
    """Raw entropy bytes plus their provenance."""

    bytes_hex: str
    source: Literal["anu_qrng", "os_csprng"]
    timestamp: float
    note: str


async def fetch_entropy(num_bytes: int = 32) -> EntropyResult:
    """Try ANU QRNG, fall back to local CSPRNG.

    `num_bytes` is clipped to [4, 256].
    """
    n = max(4, min(256, num_bytes))
    try:
        async with httpx.AsyncClient(timeout=ANU_TIMEOUT_S) as client:
            r = await client.get(ANU_URL, params={"length": n, "type": "uint8"})
            r.raise_for_status()
            payload = r.json()
            if payload.get("success") and isinstance(payload.get("data"), list):
                raw = bytes(int(x) & 0xFF for x in payload["data"])
                if len(raw) == n:
                    return EntropyResult(
                        bytes_hex=raw.hex(),
                        source="anu_qrng",
                        timestamp=time.time(),
                        note=(
                            "Entropie issue de fluctuations du vide quantique "
                            "(laboratoire ANU, mesurées par interférométrie cohérente)."
                        ),
                    )
    except Exception as exc:  # noqa: BLE001
        logger.info("ANU QRNG unavailable, falling back to OS CSPRNG: %s", exc)

    raw = secrets.token_bytes(n)
    return EntropyResult(
        bytes_hex=raw.hex(),
        source="os_csprng",
        timestamp=time.time(),
        note=(
            "Entropie système (kernel CSPRNG). Le serveur quantique ANU "
            "était indisponible — la randomness reste cryptographiquement saine."
        ),
    )


# ---------------------------------------------------------------------------
# Symbolic archetypes
# ---------------------------------------------------------------------------
#
# Each archetype has a code, a noun, a short reflection, and a "tone".
# We deliberately avoid anything that could be read as medical advice or
# fortune-telling — these are reflective prompts in the same vein as a
# "Word of the Year" exercise.

ARCHETYPES: list[dict[str, str]] = [
    {"code": "01", "name": "Patience",       "tone": "calm",    "reflection": "Ce qui doit germer ne se précipite pas. Reviens demain avec plus de douceur."},
    {"code": "02", "name": "Courage",        "tone": "fire",    "reflection": "L'action que tu redoutes contient l'information dont tu as besoin."},
    {"code": "03", "name": "Clarté",         "tone": "air",     "reflection": "Pose la question à voix haute. Le brouillard se dissipe quand on l'articule."},
    {"code": "04", "name": "Ancrage",        "tone": "earth",   "reflection": "Reviens à ton corps. Le sol existe sous tes pieds en ce moment précis."},
    {"code": "05", "name": "Mouvement",      "tone": "fire",    "reflection": "Une petite action vaut un grand plan. Choisis le premier pas, pas le meilleur."},
    {"code": "06", "name": "Repos",          "tone": "water",   "reflection": "L'arc qui ne se détend jamais perd sa flèche. Pause n'est pas paresse."},
    {"code": "07", "name": "Attention",      "tone": "air",     "reflection": "Le détail que tu as ignoré est probablement la clef."},
    {"code": "08", "name": "Joie simple",    "tone": "calm",    "reflection": "Cherche ce qui a souri en toi cette semaine, même brièvement. Suis-le."},
    {"code": "09", "name": "Limite",         "tone": "earth",   "reflection": "Un « non » net est plus généreux qu'un « oui » épuisé. À qui dois-tu dire non ?"},
    {"code": "10", "name": "Confiance",      "tone": "water",   "reflection": "Tu as déjà traversé une situation comparable. Souviens-toi comment."},
    {"code": "11", "name": "Curiosité",      "tone": "air",     "reflection": "Approche le problème comme un enfant — sans hypothèse, juste regarder."},
    {"code": "12", "name": "Présence",       "tone": "calm",    "reflection": "Trois respirations conscientes : voilà ta seule tâche pour les 30 prochaines secondes."},
    {"code": "13", "name": "Gratitude",      "tone": "water",   "reflection": "Nomme trois choses qui t'ont aidé aujourd'hui — y compris ce qui n'a pas l'air important."},
    {"code": "14", "name": "Lâcher prise",   "tone": "water",   "reflection": "Ce que tu retiens trop fort fuit entre tes doigts. Desserre une seconde."},
    {"code": "15", "name": "Discernement",   "tone": "air",     "reflection": "Toutes les options ne se valent pas. Élimine d'abord, choisis ensuite."},
    {"code": "16", "name": "Recommencer",    "tone": "fire",    "reflection": "L'erreur passée n'a aucun droit de vote sur la décision présente."},
    {"code": "17", "name": "Honnêteté",      "tone": "earth",   "reflection": "Qu'est-ce que tu sais mais que tu refuses encore de te dire ?"},
    {"code": "18", "name": "Lenteur",        "tone": "calm",    "reflection": "Ralentis exprès. Tu vas voir ce que la vitesse cachait."},
    {"code": "19", "name": "Confiance en soi", "tone": "fire",  "reflection": "Tu n'as pas besoin de permission. Personne ne te la donnera jamais entièrement."},
    {"code": "20", "name": "Tendresse",      "tone": "water",   "reflection": "Parle-toi comme à un ami que tu aimes. Pas comme à un employé en retard."},
    {"code": "21", "name": "Lumière",        "tone": "calm",    "reflection": "Cherche un endroit lumineux. Bouge ton corps de cinq mètres. Recommence à penser."},
    {"code": "22", "name": "Symbole",        "tone": "air",     "reflection": "Ton inconscient parle en images. Note la première image qui apparaît."},
]


def _pick_archetype(entropy: bytes) -> dict[str, str]:
    """Map entropy to one of the archetypes uniformly."""
    if not entropy:
        return ARCHETYPES[0]
    n = len(ARCHETYPES)
    # Use first 4 bytes as a 32-bit unsigned int, mod N (very small bias).
    idx = int.from_bytes(entropy[:4], "big") % n
    return ARCHETYPES[idx]


def _entropy_signature(entropy: bytes) -> str:
    """A short, stable, human-readable fingerprint."""
    h = hashlib.sha256(entropy).hexdigest()
    return f"{h[:4]}-{h[4:8]}-{h[8:12]}"


# ---------------------------------------------------------------------------
# Optional Mistral creative layer
# ---------------------------------------------------------------------------

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_MODEL = os.environ.get("MISTRAL_MODEL", "mistral-small-latest")
MISTRAL_TIMEOUT_S = 12.0


async def _refine_with_mistral(
    intention: str,
    archetype: dict[str, str],
    mode: Literal["emit", "receive"],
) -> str | None:
    """Ask Mistral to produce a short personalised affirmation.

    Returns `None` on any failure (missing key, network error, parse error)
    so the caller can fall back to the static archetype reflection.

    The prompt explicitly forbids any pseudo-scientific or fortune-telling
    framing — the goal is a reflective, well-written micro-text.
    """
    key = os.environ.get("MISTRAL_API_KEY")
    if not key:
        return None

    if mode == "emit":
        system = (
            "Tu es un coach calme et lettré. L'utilisateur a écrit une intention. "
            "Tu reçois aussi un mot-archétype et sa réflexion associée. Réponds en 2 à 3 "
            "phrases (40-60 mots) en français, dans un ton bienveillant et précis. "
            "Pas de promesse magique, pas de prédiction, pas d'astrologie. Tu peux "
            "reformuler l'intention plus clairement, suggérer une micro-action concrète, "
            "et nommer l'archétype comme une orientation, pas comme un oracle."
        )
        user = (
            f"Intention de l'utilisateur : « {intention.strip()} »\n"
            f"Archétype tiré : {archetype['name']} ({archetype['tone']})\n"
            f"Réflexion de base : {archetype['reflection']}\n"
            "Écris la réponse personnalisée."
        )
    else:
        system = (
            "Tu es un guide réflexif. L'utilisateur a posé une question intime ou "
            "demandé un signe. Tu reçois un archétype et sa réflexion. Réponds en 2 à 3 "
            "phrases (40-60 mots), comme un message bref et soigneux, en français. "
            "Reformule la question si nécessaire. Pas de prédiction de l'avenir, pas "
            "de jugement, pas de jargon mystique — seulement une invitation à prêter "
            "attention à un aspect de la situation."
        )
        user = (
            f"Question de l'utilisateur : « {intention.strip() or '(sans question explicite)'} »\n"
            f"Archétype tiré : {archetype['name']} ({archetype['tone']})\n"
            f"Réflexion de base : {archetype['reflection']}\n"
            "Écris la réponse personnalisée."
        )

    try:
        async with httpx.AsyncClient(timeout=MISTRAL_TIMEOUT_S) as client:
            resp = await client.post(
                MISTRAL_URL,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MISTRAL_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    "temperature": 0.6,
                    "max_tokens": 220,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return None
            content = choices[0].get("message", {}).get("content", "").strip()
            return content or None
    except Exception as exc:  # noqa: BLE001
        logger.info("Mistral refinement failed (using fallback): %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API models
# ---------------------------------------------------------------------------


class EmitRequest(BaseModel):
    intention: str = Field(min_length=1, max_length=2000)


class ReceiveRequest(BaseModel):
    question: str = Field(default="", max_length=2000)


class WaveSignal(BaseModel):
    archetype: dict[str, str]
    message: str
    signature: str
    source: Literal["anu_qrng", "os_csprng"]
    used_llm: bool
    timestamp: float


async def emit(req: EmitRequest) -> WaveSignal:
    """Send an intention. Returns a `WaveSignal` to confirm the emission."""
    entropy = await fetch_entropy(32)
    raw = bytes.fromhex(entropy.bytes_hex)
    archetype = _pick_archetype(raw)
    refined = await _refine_with_mistral(req.intention, archetype, mode="emit")
    message = refined or (
        f"{archetype['reflection']} — "
        f"Rappel : ton intention reste « {req.intention.strip()[:140]} »."
    )
    return WaveSignal(
        archetype=archetype,
        message=message,
        signature=_entropy_signature(raw),
        source=entropy.source,
        used_llm=refined is not None,
        timestamp=entropy.timestamp,
    )


async def receive(req: ReceiveRequest) -> WaveSignal:
    """Pull a signal — symbolic answer to an optional question."""
    entropy = await fetch_entropy(32)
    raw = bytes.fromhex(entropy.bytes_hex)
    archetype = _pick_archetype(raw)
    refined = await _refine_with_mistral(req.question, archetype, mode="receive")
    message = refined or archetype["reflection"]
    return WaveSignal(
        archetype=archetype,
        message=message,
        signature=_entropy_signature(raw),
        source=entropy.source,
        used_llm=refined is not None,
        timestamp=entropy.timestamp,
    )


# Convenience sync wrapper used in tests where we don't want async machinery.
def emit_sync(req: EmitRequest) -> WaveSignal:
    return asyncio.run(emit(req))


def receive_sync(req: ReceiveRequest) -> WaveSignal:
    return asyncio.run(receive(req))
