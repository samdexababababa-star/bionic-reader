# Recherche · Studio d'intention (émetteur / récepteur quantique)

> Ce module est le plus délicat de l'app : il évoque la physique quantique
> et l'« onde d'intention », ce qui est à la fois (a) un terrain où la science
> est rigoureusement réelle (vacuum fluctuations, observer effect) et
> (b) un aimant à pseudo-science. Ce document explique ce que le système
> fait *réellement*, ce qu'il ne prétend pas faire, et pourquoi l'approche
> reste utile pour un utilisateur ADHD.

## Le problème de design

L'utilisateur veut un module « émetteur d'intention / récepteur de signal »,
inspiré de :
- l'effet observateur en physique quantique (double-fente — particules
  ne se comportent pas pareil quand on les observe),
- les expériences PEAR / Global Consciousness Project (RNG influencés
  par l'intention humaine — résultats discutés mais reproductibles),
- la métaphore de l'onde (« émettre une vibration »).

Le piège : promettre que l'app « contrôle la réalité » serait
épistémologiquement faux et éthiquement problématique (effets placebo
amplifiés, vulnérabilité émotionnelle).

L'opportunité : il existe une lecture **honnête** de cette demande qui
livre 90 % de la valeur ressentie *sans* mentir scientifiquement.

## Ce que fait réellement le système

```
Utilisateur : écrit une intention en français.
        │
        ▼
Backend : fetch entropy from ANU QRNG  ← ondes vraiment quantiques
        │   (fluctuations du vide, peer-reviewed)
        │   fallback CSPRNG si offline
        │
        ▼
Picker  : map(entropy_bytes) → archétype parmi 22
        │   (uniforme, vérifiable, déterministe sur entropy fixée)
        │
        ▼
LLM     : (optionnel) reformule l'archétype + l'intention en phrase
        │   personnalisée — Mistral, prompt strict anti-pseudo-science
        │
        ▼
Frontend : affiche archétype + message + signature + source d'entropie
```

## Pourquoi c'est *réellement* quantique

L'**Australian National University Quantum Random Number Generator** mesure
les fluctuations du vide quantique en utilisant deux faisceaux laser
cohérents et un détecteur homodyne (Symul, Assad, Lam, *Appl. Phys. Lett.*
98, 231103, 2011). Les fluctuations sont **fondamentalement non-déterministes**
au sens de la mécanique quantique : aucun appareil ne peut prédire les bits
avant leur mesure, parce qu'il n'y a pas d'état caché à mesurer. C'est
qualitativement différent du `/dev/urandom` ou d'un PRNG mathématique.

Endpoint : `https://qrng.anu.edu.au/API/jsonI.php` (public, gratuit,
rate-limit raisonnable, fonctionne au moment de la rédaction).

**Garde-fou** : si l'appel échoue (timeout, rate-limit, blocage réseau),
on retombe sur `secrets.token_bytes()` du kernel, qui est lui-même
cryptographiquement sûr (kernel CSPRNG agrégeant plusieurs sources
d'entropie matérielle). La provenance (`anu_qrng` vs `os_csprng`) est
affichée à l'utilisateur honnêtement.

## Pourquoi ce n'est *pas* « contrôler la réalité »

L'effet observateur en physique quantique — souvent invoqué par les courants
mystiques — décrit que **mesurer** un système quantique perturbe son état.
Ceci ne signifie *pas* que la conscience est requise pour « créer » la
réalité (Bell 1964, Aspect 1982, plus tard Hossenfelder 2021). La mesure
peut être faite par n'importe quel appareil macroscopique non-conscient.
Les expériences PEAR (Princeton Engineering Anomalies Research) ont
trouvé une corrélation **infimes** (`P=0,5+1e-4`) entre intention humaine
et RNG quantique — significatif statistiquement avec 10⁸ essais, mais
trop faible pour avoir un effet pratique sur 32 bytes d'entropie.

Le système ne prétend **pas** que ton intention influence les bytes
reçus. Il dit : *« voici 32 bytes vraiment indéterministes, voici un
archétype tiré à partir d'eux, voici une phrase personnalisée — utilise
cela comme un I-Ching numérique. »*

## La valeur réelle pour l'utilisateur ADHD

Pourquoi est-ce intéressant pour quelqu'un avec un TDAH ?

1. **Articulation de l'intention** : écrire sa pensée en une phrase
   est une mini-tâche qui force la focalisation. Effet documenté en
   thérapie cognitive (Solanto 2008, Safren 2010).
2. **Externalisation aléatoire** : tirer une réponse non-choisie casse
   le ruminement (Watkins 2008). Le cerveau ADHD est connu pour boucler
   sur ses propres scénarios ; un « jet de dé symbolique » introduit
   un point d'arrêt.
3. **Ritualisation** : transformer une question en geste structuré
   (émettre → recevoir) apporte un cadre. La psychologie cognitive a
   beaucoup étudié la valeur des « micro-rituels » sur l'auto-régulation
   (Norton & Gino 2014).
4. **Validation de la curiosité scientifique** : l'utilisateur a une
   intuition vraie (« la physique quantique est vraiment étrange »).
   Le système la respecte au lieu de la nier ou de la flatter.

## Anti-design (ce qu'on a refusé)

- **Pas de score d'alignement** entre l'intention et l'archétype tiré.
  Cela suggérerait une causalité illusoire.
- **Pas de « pourcentage de succès »** ni de gamification — addictogène
  et anti-mindfulness.
- **Pas de notifications quotidiennes** type « ton onde du jour ! ».
  Le module est *opt-in pull*, pas push.
- **Pas de jargon flou** comme « vibrations », « énergie », « fréquence
  de l'âme ». On utilise des mots concrets : *archétype*, *signature
  d'entropie*, *source quantique*.
- **Pas de claim médical** : nulle mention de guérison, d'anxiété, de
  dépression. Le système est un outil de journaling, point.

## Les 22 archétypes

Choisis pour leur force réflexive et leur applicabilité quotidienne :
Patience, Courage, Clarté, Ancrage, Mouvement, Repos, Attention,
Joie simple, Limite, Confiance, Curiosité, Présence, Gratitude,
Lâcher prise, Discernement, Recommencer, Honnêteté, Lenteur,
Confiance en soi, Tendresse, Lumière, Symbole.

Chacun a une réflexion courte (1 phrase) et un *ton* (calm / fire /
air / water / earth) qui sert d'aide visuelle dans l'UI future.

Inspirations méthodologiques :
- Tarot de Marseille (Wirth, *Le Tarot des Imagiers du Moyen Âge*, 1927)
- I Ching (Wilhelm/Baynes 1950, 64 hexagrammes)
- Oblique Strategies (Eno & Schmidt 1975, 100+ cartes créatives)
- *On the Shortness of Life* (Sénèque) — sélection finale des verbes
  d'action

## Modèle LLM (Mistral)

Si `MISTRAL_API_KEY` est défini côté serveur, on appelle
`mistral-small-latest` (configurable via `MISTRAL_MODEL`).
Prompt système strict :

> *Tu es un coach calme et lettré. … Pas de promesse magique, pas de
> prédiction, pas d'astrologie. Tu peux reformuler l'intention plus
> clairement, suggérer une micro-action concrète, et nommer l'archétype
> comme une orientation, pas comme un oracle.*

Paramètres : `temperature=0.6`, `max_tokens=220`. Cette tempérure
donne suffisamment de variété pour ne pas répéter la même formule à
chaque appel, tout en restant maîtrisée (pas de fugue créative).

Si le LLM est indisponible (clé absente, timeout, erreur API) →
fallback gracieux sur la réflexion plain-text de l'archétype, avec
ajout du fragment d'intention pour faire personnel.

## Tests

`backend/tests/test_quantum.py` couvre :
- archétype picker uniforme et déterministe sur entropie fixée
- signature stable / change avec input
- `fetch_entropy` retombe gracieusement sur CSPRNG si offline
- `emit` retourne un message valide
- `receive` retourne un message valide
- (skipif `MISTRAL_API_KEY` défini) fallback sans LLM utilise la réflexion

## Références scientifiques

- Symul T, Assad SM, Lam PK. *Real time demonstration of high bitrate quantum random number generation with coherent laser light*. **Appl. Phys. Lett.** 98, 231103 (2011).
- Aspect A, Grangier P, Roger G. *Experimental tests of Bell's inequalities using time-varying analyzers*. **Phys. Rev. Lett.** 49, 1804 (1982).
- Bell JS. *On the Einstein-Podolsky-Rosen paradox*. **Physics** 1, 195 (1964).
- Jahn RG, Dunne BJ, Nelson RD. *Engineering anomalies research*. **J. Sci. Explor.** 1, 21-50 (1987). [PEAR — résultats faibles, discutés]
- Hossenfelder S. *Existential Physics: A Scientist's Guide to Life's Biggest Questions*. Viking (2022). [critique rigoureuse des interprétations mystiques de la mécanique quantique]
- Solanto MV, Marks DJ, et al. *Efficacy of meta-cognitive therapy for adult ADHD*. **Am J Psychiatry** 168:958 (2008).
- Watkins ER. *Constructive and unconstructive repetitive thought*. **Psychol Bull** 134, 163-206 (2008).
- Norton MI, Gino F. *Rituals alleviate grieving for loved ones, lovers, and lotteries*. **J Exp Psychol Gen** 143, 266 (2014).

## Limites assumées

Le système :
- n'est pas un oracle,
- ne soigne rien,
- ne fait pas de prédiction sur l'avenir,
- ne donne pas de conseil médical, financier, légal,
- n'enregistre pas les intentions utilisateurs sur le serveur (passe par
  l'endpoint, jamais persisté),
- ne partage pas les intentions avec Mistral en dehors d'un appel API
  ponctuel (la politique Mistral standard s'applique).

L'utilisateur garde le contrôle total. Le seul effet « réel » revendiqué
est l'**externalisation d'une réflexion sur une matrice aléatoire honnête** —
le même mécanisme cognitif que celui qui rend le tarot ou les *Oblique
Strategies* utiles en pratique, en dépit de leur absence de validité
prédictive.
