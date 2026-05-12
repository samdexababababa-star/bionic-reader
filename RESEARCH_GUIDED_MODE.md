# Recherche · Mode guidé v2 (calibration TDAH scientifiquement fondée)

> Approche multi-équipes adversariale : neuropsy clinicien, UX designer ADHD-aware,
> ingénieur backend, sceptique méthodologique. À chaque idée, l'équipe sceptique
> attaque, on ne garde que ce qui survit. Document = sortie de ce processus.

## Constat — pourquoi la v1 ne suffisait pas

Le mode guidé v1 était un questionnaire déclaratif en 6 questions de préférence :
*« préfères-tu un fond clair ou sombre ? »*, *« lis-tu rapidement ou lentement ? »*, etc.
Trois problèmes :

1. **Biais d'auto-évaluation**. Les personnes ADHD se sous-estiment ou se sur-estiment
   souvent (Mannuzza 2002 ; Sibley 2014). Demander *« tu es distrait ? »* à un
   adulte ADHD revient à demander à un poisson s'il sait nager.
2. **Pas d'ancrage scientifique**. Aucun item ne mappe à un sous-type DSM-5
   (inattentif / hyperactif-impulsif / combiné) ni à une dimension cognitive
   mesurable. Le préset retourné n'avait aucune justification clinique.
3. **Pas de différenciation**. Quatre presets, six questions textuelles → quatre
   trajets binaires dans un arbre — pas de mesure continue.

## Design v2 — trois sources de données complémentaires

### 1. ASRS-v1.1 Part A — questionnaire validé OMS (Kessler et al. 2005)

Six items au format Likert 0–4 (Jamais → Très souvent). Validé sur
> 60 000 sujets dans 11 pays via les enquêtes WHO World Mental Health.
Sensibilité 68,7 %, spécificité 99,5 % pour un score positif (≥ 4 items « darkened »
selon le seuil per-item OMS — items 1-4 à ≥ 2 « Parfois », items 5-6 à ≥ 3 « Souvent »).

**Pourquoi pas le WURS-25 ou les CAARS ?**
- WURS-25 est rétrospectif (« étant enfant »), peu pertinent pour calibrer une session de lecture *maintenant*.
- CAARS est long (66 items) et propriétaire (Multi-Health Systems).
- BAARS-IV est solide mais payant et requiert 30 min.
- ASRS Part A = 6 items, 30 s, libre de droits, recommandé OMS — c'est la borne supérieure réaliste pour un onboarding.

**Limite assumée** : reste déclaratif. C'est pourquoi on combine avec deux mesures comportementales.

### 2. PVT — Psychomotor Vigilance Task (Dinges & Powell 1985)

Tâche d'attention soutenue, gold-standard en sleep medicine, robuste sur ADHD
(Tucha 2009, Cassuto 2013).

- 16 essais à délai aléatoire 2–6 s.
- L'utilisateur clique dès que le stimulus apparaît.
- Métriques : RT médian, RT moyen, lapses (RT > 500 ms), faux départs (clic avant stimulus).

**Norms** :
- Adulte sain reposé : RT médian 250–290 ms, lapses < 5 % des essais.
- ADHD : RT médian souvent 330–400 ms, variabilité ↑ (variance ↑), lapses ≥ 15 % des essais.
- Hyperactivité-impulsivité : faux départs ↑ (anticipation prématurée).

Ces signatures sont mappées vers les dimensions :
- `processing_speed` = inverse linéaire normalisé du RT médian sur [220 ms, 500 ms].
- `distraction_sensitivity` = montée linéaire avec les lapses au-delà du baseline 1 / 20.
- `hyperactivity_impulsivity_pvt` = montée linéaire avec les faux départs.

**Pourquoi pas le n-back, le Stroop, ou le Conners CPT ?**
- n-back : excellent pour la mémoire de travail mais nécessite **> 5 min** et beaucoup de feedback visuel — incompatible avec un onboarding de 90 s.
- Stroop : trop dépendant de la performance lecture (or on calibre justement la lecture).
- Conners CPT : 14 min, propriétaire. Pas viable.

Le PVT est le seul test d'attention soutenue qui tient en 30 s et qui mesure quelque chose de **différent** de ce que demande l'ASRS.

### 3. Test de lecture courte (60 mots)

Mesure : vitesse de lecture confortable (WPM) + difficulté ressentie (échelle 0–4).
Cap empirique [40, 900] WPM pour rejeter les valeurs pathologiques (clic accidentel, distraction prolongée).

Sert deux dimensions :
- `working_memory` (corrélée à la difficulté ressentie),
- `processing_speed` (corrélée à la vitesse).

**Limite assumée** : c'est une seule lecture, courte. Une calibration cliniquement valide demanderait plusieurs paragraphes et une question de compréhension. Pour un onboarding, c'est le maximum supportable.

## Mapping dimensions → preset

Cinq dimensions interprétables sont calculées :

| Dimension                  | Source principale                                  |
|----------------------------|---------------------------------------------------|
| `inattention`              | ASRS items 1-4 + RT lent + lapses                 |
| `hyperactivity_impulsivity`| ASRS items 5-6 + faux départs PVT                 |
| `working_memory`           | difficulté ressentie en lecture                    |
| `processing_speed`         | RT médian PVT + WPM                               |
| `distraction_sensitivity`  | lapses PVT                                        |

Quatre presets bionic sont ensuite scorés par combinaison linéaire transparente.
L'utilisateur voit ces scores en barres + le rationale en langage clair.

### Pourquoi un modèle linéaire transparent et pas un ML ?

Avec N=1 utilisateur par session, l'apprentissage automatique = bruit. Le scoring
ASRS lui-même est une règle linéaire à coefficients fixés ; on suit cette tradition.
Plus important : **l'utilisateur doit pouvoir comprendre pourquoi** on lui propose
le preset « Concentré » plutôt que « Apaisé ». Le rationale est généré à partir
des dimensions qui ont franchi un seuil (`inattention >= 0.7` → « tendance
inattentive marquée »), pas à partir d'une boîte noire.

## Confiance

Reflet honnête de la quantité d'info disponible :

| Source manquante      | Pénalité confiance |
|-----------------------|--------------------|
| ASRS partiel ou skip  | jusqu'à -10 %      |
| PVT skip              | -40 %              |
| Lecture skip          | -40 %              |
| Tout passer           | confiance = 10 %   |

Confiance < 30 % → on affiche un disclaimer doux : *« tu as choisi de tout passer
— on te propose un profil par défaut »*. Pas de mensonge, pas de pseudo-science.

## UX ADHD-aware

Cinq étapes, jamais plus de **5 unités cognitives** à l'écran (limite de Barkley 2012
pour la mémoire de travail en charge).

- **Progress visible** (barre de 5 points) — recommandation Csikszentmihalyi (flow exige feedback).
- **Tap targets ≥ 44 px** — Fitt's law, accessibilité mobile.
- **Couleurs douces parchemin** (theme paper) — réduit la fatigue visuelle (Irlen 1991).
- **Skipping toléré sur chaque étape** — pas de friction punitive.
- **Latence < 100 ms** sur transitions — micro-feedback immédiat (Norman 2013).
- **Pas de jargon clinique** dans l'UI utilisateur : « Très souvent » plutôt que « Likert 4 ».
- **Pas de score chiffré humiliant** : on parle de *profil*, pas de *diagnostic*.

## Tests adversariaux qui ont survécu

> **Sceptique** : « Comment éviter le biais d'optimisation — l'utilisateur clique
> rapidement sur le PVT juste pour finir ? »

Réponse : le PVT a des faux départs comptés et pénalisants. Cliquer trop vite
sans stimulus est détecté et taxe la dimension impulsivité. C'est exactement
le comportement que la littérature documente chez les hyperactifs-impulsifs
(Solanto 2001), donc le système n'est pas trompé — il l'interprète correctement.

> **Sceptique** : « Et si l'utilisateur clique exactement *jamais* ? »

Réponse : le scoreur tolère un PVT vide (`trials=0`) et renvoie des
dimensions neutres. Confiance ↓ pour signaler le défaut d'info. Pas de crash.

> **Sceptique** : « Comment je sais que le test de lecture n'a pas été
> sauté en collant un tab + entrée ? »

Réponse : le ré-rendu du paragraphe en clair (non flouté) demande un clic
explicite « Démarrer ». Si la session dure < 1 s, le clamp [40, 900 WPM]
fait que la dimension processing_speed atteint son max (1.0) mais
working_memory n'est pas modifiée (skip difficulté). Le rationale dira
« vitesse élevée », un sprint pourra être proposé — comportement
cohérent même sous gaming.

> **Sceptique** : « Le test n'est pas un diagnostic clinique. C'est
> mensonger de prétendre le contraire. »

Réponse : on ne le prétend nulle part. L'UI dit explicitement
« calibration · profil de lecture » et le footer rappelle
*« tes réponses servent uniquement à choisir un des 4 presets »*.
Aucun champ n'utilise le mot *diagnostic*, *trouble*, ou *patient*.

## Références

- Kessler RC, Adler L, Ames M, et al. *The World Health Organization Adult ADHD Self-Report Scale (ASRS): a short screening scale for use in the general population*. **Psychol Med** 2005;35:245-256.
- Adler LA, Spencer T, Faraone SV, et al. *Validity of pilot Adult ADHD Self-Report Scale (ASRS) to rate adult ADHD symptoms*. **Ann Clin Psychiatry** 2006;18:145-148.
- Dinges DF, Powell JW. *Microcomputer analyses of performance on a portable, simple visual RT task during sustained operations*. **Behav Res Methods** 1985;17:652-655.
- Solanto MV, Abikoff H, Sonuga-Barke E, et al. *The ecological validity of delay aversion and response inhibition as measures of impulsivity in AD/HD*. **J Abnorm Child Psychol** 2001;29:215-228.
- Tucha O, Walitza S, Mecklinger L, et al. *Attentional functioning in children with ADHD — predominantly hyperactive-impulsive type and children with ADHD — combined type*. **J Neural Transm** 2006;113:1943-1953.
- Cassuto H, Ben-Simon A, Berger I. *Using environmental distractors in the diagnosis of ADHD*. **Front Hum Neurosci** 2013;7:805.
- Sibley MH, Pelham WE, Molina BSG, et al. *The validity of a brief ADHD diagnostic interview for adults*. **Psychol Assess** 2012;24:879-891.
- Mannuzza S, Klein RG, Klein DF, et al. *Accuracy of adult recall of childhood attention deficit hyperactivity disorder*. **Am J Psychiatry** 2002;159:1882-1888.
- Castellanos FX, Sonuga-Barke EJS, Milham MP, Tannock R. *Characterizing cognition in ADHD: beyond executive dysfunction*. **Trends Cogn Sci** 2006;10:117-123.
- Barkley RA. *Executive Functions: What They Are, How They Work, and Why They Evolved*. Guilford 2012.
- Csikszentmihalyi M. *Flow: The Psychology of Optimal Experience*. Harper 1990.
- Norman DA. *The Design of Everyday Things*, revised edition. Basic Books 2013.
- Irlen H. *Reading by the Colors*. Avery 1991.

## État courant des tests automatisés

`backend/tests/test_calibration.py` couvre :
- scoring ASRS (positif/négatif)
- mapping sous-type inattentif → preset {apaise, concentre}
- mapping hyperactif-impulsif → sprint
- mid-range → jamais sprint
- skip total → confiance ≤ 15 %
- toutes données → confiance = 100 % et affinités somment à 1.0
- rationale est une phrase < 500 caractères avec « Détecté » + « Réglage suggéré »

7 tests, tous verts.
