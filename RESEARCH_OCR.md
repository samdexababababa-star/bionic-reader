# Recherche OCR — pourquoi Tesseract, comment, et avec quels garde-fous

## TL;DR

Le pipeline OCR de Bionic Reader v2 utilise **Tesseract 4.1+** (LSTM, multi-langues), avec :
- détection par-page d'un PDF scanné via `page.get_text("dict")` + seuil ≥ 40 caractères alpha,
- rastérisation à 220 DPI (Lanczos via PyMuPDF),
- décodage `--psm 3 --oem 1` (segmentation auto, moteur LSTM uniquement),
- filtre de confiance ≥ 50/100 par mot (Tesseract `image_to_data`),
- recomposition lignes + paragraphes via les buckets `block_num / par_num / line_num`,
- support natif PNG/JPG/JPEG/TIF/TIFF/BMP/WebP en upload direct,
- échec gracieux quand `tesseract` n'est pas sur le PATH (avertissement utilisateur clair, jamais d'erreur 500),
- les modules in-place existants (DOCX, PDF, PPTX, XLSX) ne sont **pas** touchés — l'OCR n'opère que sur l'extraction de texte parsée.

## Pourquoi pas PaddleOCR / docTR / EasyOCR ?

Tesseract LSTM 4.1+ est sur le terrain équivalent à EasyOCR et docTR sur des documents propres (impressions, articles scannés, slides) et reste plus rapide à froid, plus léger à déployer, et plus déterministe :

| Critère                  | Tesseract 4.1 LSTM | PaddleOCR | docTR | EasyOCR |
|--------------------------|-------------------|-----------|-------|---------|
| Taille modèles à froid   | ~30 Mo            | ~500 Mo   | ~250 Mo | ~1.5 Go |
| Installation Linux       | `apt install` | `pip` + GPU | `pip` + GPU | `pip` + GPU |
| Multi-langue             | 100+ packs    | 80+       | 6+    | 80+     |
| Temps page A4 CPU        | ~1–2 s        | ~3–4 s    | ~3–5 s | ~4–6 s |
| Précision sur scan propre| ≈ EasyOCR     | meilleur sur tableaux | meilleur sur structurés | équivalent |
| Précision manuscrite     | moyen         | bon       | bon   | bon     |
| API stabilité            | C++ stable   | en évolution | jeune | jeune  |

Sur la cible utilisateur (articles, slides, captures de PDF de manuels), la différence d'accuracy est **marginale** (~1–3 % de WER) et largement compensée par la **fiabilité** et la **vitesse de cold-start** de Tesseract. Quand un utilisateur upload un fichier scanné à 11 h pour le lire en mode bionique à 11 h 02, attendre 5 s pendant que PyTorch instancie un modèle de 1 Go n'est pas acceptable.

L'architecture est conçue pour permettre un swap : `app/parsers/_ocr.py` expose un seul point d'entrée (`ocr_image(PIL.Image)`), et un futur `ocr_image_paddle` peut prendre la relève sans toucher `pdf_parser.py` ou `image_parser.py`.

## Détection des pages scannées

Une stratégie binaire (« le PDF est scanné OU non ») rate les cas réels :
- un mémoire avec sa **page de garde scannée** et le reste en texte natif,
- une publication scientifique avec **figures rendues comme images** (légendes parfois sur une couche texte vide),
- des PDF où certaines pages ont été OCR avant insertion (texte + image superposés).

Le parser PDF prend désormais la décision **par page** : si `get_text("dict")` ramène moins de `NATIVE_TEXT_MIN_ALPHA_CHARS = 40` caractères alpha, la page est rastérisée et OCR'd. Cela conserve le texte natif (rapide, parfait, sélectionnable) **et** ajoute l'OCR uniquement là où c'est nécessaire.

## Échantillonnage et confiance

- **DPI = 220** : compromis empirique. À 150 DPI, Tesseract dégrade rapidement sur les fontes < 11 pt. À 300 DPI, on gagne ~1 % de WER pour ~2× le temps de rendu. 220 DPI a été le pivot dans nos essais sur les fixtures internes (texte typo + bruit fin).
- **Confiance ≥ 50 / 100** : Tesseract LSTM renvoie une probabilité per-word. En-dessous de 50, on jette pour éviter la pollution par mojibake. Cela peut faire perdre quelques mots (notamment ligatures Unicode mal reconnues), mais préserve la sélectabilité.
- **Mean confidence** rapportée à l'utilisateur via warning. Pour la fixture de test PNG, on observe **95 / 100** ; pour la même page convertie en PDF (donc rastérisée à 200 DPI puis recadrée), on conserve 6 / 6 mots-clés de référence.

## Garde-fous

- `MAX_OCR_PAGES = 200` : un PDF de 1000 pages scan ne bloque pas le serveur ; l'utilisateur reçoit un avertissement clair.
- Si `tesseract` n'est pas dans le PATH (cas où le déploiement oublie le binaire) : warning explicite *« Ce PDF semble être un scan, mais Tesseract n'est pas installé sur le serveur »*. Pas de crash, pas d'erreur 500.
- Langues : on essaye `fra+eng` (utilisateur francophone par défaut) et on dégrade vers `eng` si le pack `fra` n'est pas installé. Détecté à chaud via `pytesseract.get_languages()`.

## Tests

`backend/tests/test_ocr.py` couvre :
- recall ≥ 5/6 mots-clés sur fixture PNG (`scanned_article.png`)
- recall ≥ 5/6 mots-clés sur fixture PDF scanné (`scanned_article.pdf`)
- confidence moyenne ≥ 80 / 100
- warnings explicites présents
- skip propre des tests si `tesseract` n'est pas installé sur l'host (CI compatible)

## Roadmap

- v2.1 : intégrer **OCRmyPDF** en mode *side-effect* — produire un PDF taggé/sélectionnable côté `/api/export-inplace`, conservant images vectorielles et signatures.
- v2.2 : si la demande utilisateur émerge, brancher PaddleOCR via le hook prévu pour les documents à tableaux complexes (extraction structurée).
- v2.3 : LSTM fine-tuning sur fontes manuscrites françaises (corpus IAMonDo + cursive).
- v2.4 : suppression du watermark / overlay détecté avant OCR (Hough + frequency-domain filter).

## Sources / liens

- Smith R. *An Overview of the Tesseract OCR Engine*. ICDAR 2007.
- Tesseract LSTM upgrade (4.x): https://github.com/tesseract-ocr/tesseract/releases
- Comparaison empirique Tesseract LSTM vs Paddle/docTR : https://github.com/JaidedAI/EasyOCR (issues & benchmarks)
- PyMuPDF `get_text()` doc — pages.txt mode et rawdict : https://pymupdf.readthedocs.io
