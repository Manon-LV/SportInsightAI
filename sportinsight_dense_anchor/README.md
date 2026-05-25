# SportInsight AI — Dense Temporal Anchor Spotter

Implémentation PyTorch d'un modèle d'**action spotting** pour SoccerNet, inspiré du papier :

> Soares, J. V. B. & Shah, A. *Action Spotting using Dense Detection Anchors Revisited*. SoccerNet Challenge / arXiv, 2022.

Le modèle est une version légère adaptée au projet SportInsight AI : il utilise les **features SoccerNet ResNet PCA512** et prédit, pour chaque ancre temporelle :

1. une probabilité d'action pour chaque classe ;
2. un offset temporel pour raffiner le timestamp de l'action.

Classes ciblées par défaut :

- `Goal`
- `Corner`
- `Yellow card`
- `Red card`

---

## 1. Installation

```bash
cd sportinsight_dense_anchor
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
pip install -e .
```

Vérification rapide sans SoccerNet :

```bash
python scripts/sanity_check.py
```

Ce script crée un mini jeu de données synthétique, lance une passe d'entraînement et vérifie l'inférence.

---

## 2. Structure attendue des données SoccerNet

Le loader scanne récursivement les dossiers contenant un fichier `Labels-v2.json` et des features :

```text
SOCCERNET_ROOT/
├── england_epl/2014-2015/2015-02-21 - .../
│   ├── Labels-v2.json
│   ├── 1_ResNET_PCA512.npy
│   └── 2_ResNET_PCA512.npy
└── ...
```

Les fichiers de features peuvent aussi avoir un nom proche contenant `1_`, `2_`, `ResNET` et `PCA512`.

---

## 3. Entraînement

Modifier `configs/default.yaml`, puis lancer :

```bash
python -m sportinsight.train --config configs/default.yaml
```

Les checkpoints sont sauvegardés dans `runs/dense_anchor/`.

---

## 4. Inférence sur un match SoccerNet

```bash
python -m sportinsight.infer \
  --checkpoint runs/dense_anchor/best.pt \
  --game-dir /path/to/match_dir \
  --output predictions.json
```

Sortie JSON :

```json
[
  {"half": 1, "timestamp": 754.3, "gameTime": "1 - 12:34", "label": "Corner", "score": 0.81},
  {"half": 1, "timestamp": 2535.0, "gameTime": "1 - 42:15", "label": "Goal", "score": 0.88}
]
```

---

## 5. Visualisations générées

Pendant l'entraînement, le script sauvegarde automatiquement :

```text
runs/dense_anchor/
├── history.json
├── history.csv
└── plots/
    ├── loss_curves.png
    ├── loss_components.png
    └── learning_rate.png
```

Les figures peuvent aussi être régénérées manuellement :

```bash
python scripts/plot_training_curves.py --run-dir runs/dense_anchor
```

Après inférence, une timeline des prédictions peut être produite :

```bash
python scripts/plot_timeline.py \
  --predictions predictions.json \
  --labels /path/to/match_dir/Labels-v2.json \
  --output runs/dense_anchor/timeline_match.png
```

Dans cette timeline, les cercles correspondent aux prédictions et les croix aux annotations, si un fichier `Labels-v2.json` est fourni.

---

## 6. Architecture

```text
Features ResNet PCA512
        ↓
Projection 512 → hidden_dim
        ↓
Backbone temporel U-Net 1D ou TCN dilatée
        ↓
Deux têtes :
  - classification : logits [T, C]
  - régression : offsets temporels [T, C]
        ↓
NMS temporelle par classe
        ↓
Timeline : classe + timestamp + score
```

---

## 7. Loss

La loss totale est :

```text
L = lambda_cls * L_cls + lambda_reg * L_reg
```

- `L_cls` : Focal BCE pondérée par classe ;
- `L_reg` : Smooth L1 sur les offsets, uniquement pour les ancres positives.

Cette formulation est adaptée au déséquilibre massif entre les instants sans action et les rares événements `Goal`, `Corner`, `Yellow card`, `Red card`.

---

## 8. Fichiers principaux

```text
src/sportinsight/data.py         # Dataset SoccerNet + labels denses
src/sportinsight/model.py        # DenseAnchorSpotter, U-Net 1D, TCN
src/sportinsight/losses.py       # Focal loss + Smooth L1 offset
src/sportinsight/postprocess.py  # NMS / Soft-NMS temporel
src/sportinsight/metrics.py      # AP/mAP temporelle simplifiée
src/sportinsight/train.py        # Boucle d'entraînement
src/sportinsight/infer.py        # Inférence et export JSON
```

---

## 9. Jalon 3 — interface produit et ablation modèle

### 9.1 Ablation sans projection 512 → 256

La configuration `configs/no_projection.yaml` retire la projection linéaire d'entrée et conserve les features ResNet PCA512 dans leur dimension originale.
Le bloc d'entrée devient :

```text
LayerNorm(512) → Dropout
```

Lancer l'expérience :

```bash
python -m sportinsight.train --config configs/no_projection.yaml
```

Comparer ensuite avec la baseline :

```text
runs/dense_anchor/                 # baseline avec projection 512 → 256
runs/dense_anchor_no_projection/   # ablation sans projection
```

### 9.2 Extension expérimentale à 10 classes

La configuration `configs/classes_10.yaml` prépare l'extension produit à :

```text
Goal, Corner, Yellow card, Red card, Penalty, Substitution, Offside, Foul, Shots on target, Shots off target
```

Avant entraînement sérieux, recalculer les poids de classes sur votre sous-ensemble SoccerNet :

```bash
python scripts/count_events.py \
  --root data/SoccerNet \
  --classes Goal Corner "Yellow card" "Red card" Penalty Substitution Offside Foul "Shots on target" "Shots off target"
```

### 9.3 Backend FastAPI

L'API expose l'inférence sous forme de service produit.

```bash
pip install fastapi uvicorn pydantic
uvicorn apps.api.main:app --reload --port 8000
```

Endpoints utiles :

```text
GET  /health
GET  /matches?root=data/SoccerNet
GET  /checkpoints?root=runs
POST /inference/run
GET  /runs/{run_id}/events
GET  /runs/{run_id}/summary
```

Exemple de requête :

```json
{
  "match_dir": "data/SoccerNet/example_match",
  "checkpoint": "runs/dense_anchor/best.pt",
  "half": "both",
  "score_threshold": 0.3,
  "nms_radius_sec": 6.0,
  "selected_classes": ["Goal", "Corner", "Yellow card", "Red card"],
  "device": "auto"
}
```

### 9.4 Frontend Vue 3 + Quasar

L'interface se trouve dans `apps/web`.

```bash
cd apps/web
npm install
npm run dev
```

Le frontend appelle par défaut `http://localhost:8000`.

La page principale `AnalystRoom` contient :

```text
- panneau de sélection du match, checkpoint, mi-temps, seuil et NMS ;
- timeline SVG interactive par mi-temps ;
- panneau d'événements détectés ;
- rapport automatique avec comptage par classe.
```


### Test rapide de l'interface avec le JSON propre

Le frontend contient maintenant `apps/web/public/demo_predictions_clean.json`, construit à partir d'une sortie d'inférence filtrée à `score_threshold = 0.70`. Il permet de tester la timeline sans lancer le backend.

```bash
cd apps/web
npm install
npm run dev
```

Dans l'interface, cliquer sur **Charger la démo JSON propre**. La timeline doit afficher 19 événements sur les deux mi-temps.

### Prévisualisation vidéo dans l'interface

L'interface peut afficher l'extrait vidéo autour d'une action sélectionnée, mais uniquement si les fichiers vidéo locaux sont présents. Les features `.npy` permettent l'inférence, mais elles ne permettent pas de reconstruire la vidéo.

Place les vidéos dans le dossier du match :

```text
data/SoccerNet/.../match/
├── Labels-v2.json
├── 1_ResNET_PCA512.npy
├── 2_ResNET_PCA512.npy
├── 1.mp4   # première mi-temps, recommandé
└── 2.mp4   # deuxième mi-temps, recommandé
```

Les noms `1.mkv` et `2.mkv` sont aussi détectés. Pour une démo web fiable, privilégie `.mp4`, car certains navigateurs lisent mal les `.mkv`.

---

## 10. Téléchargement des vidéos SoccerNet

L'interface peut maintenant afficher un extrait vidéo lorsqu'une action est sélectionnée. Pour cela, les vidéos SoccerNet doivent être présentes localement dans le dossier du match, à côté de `Labels-v2.json` et des features `.npy`.

Les vidéos SoccerNet nécessitent le mot de passe fourni après signature du NDA SoccerNet. Pour une démo fluide, utiliser la résolution `224p`.

### 10.1 Depuis l'interface

1. Lancer le backend :

```powershell
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

2. Lancer le frontend :

```powershell
cd apps/web
npm install
npm run dev
```

3. Ouvrir **Paramètres avancés** puis **Téléchargement SoccerNet**.
4. Renseigner le mot de passe NDA et cliquer sur **Télécharger vidéos**.

### 10.2 En ligne de commande

Un script dédié est fourni :

```powershell
python scripts/download_soccernet_videos.py `
  --root data/SoccerNet `
  --password "MOT_DE_PASSE_NDA" `
  --resolution 224p `
  --split train valid test
```

Télécharger un seul match :

```powershell
python scripts/download_soccernet_videos.py `
  --root data/SoccerNet `
  --password "MOT_DE_PASSE_NDA" `
  --resolution 224p `
  --game "england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley"
```

Il est aussi possible de définir le mot de passe dans l'environnement :

```powershell
$env:SOCCERNET_PASSWORD="MOT_DE_PASSE_NDA"
python scripts/download_soccernet_videos.py --root data/SoccerNet --resolution 224p --split train valid test
```

Détails : voir `docs/soccernet_video_download.md`.

## Split train / validation / test par match

Le projet supporte désormais un protocole propre par match. Avant un entraînement sérieux, génère les fichiers de split :

```powershell
python scripts/create_splits.py `
  --root data/SoccerNet `
  --output-dir splits `
  --train-ratio 0.70 `
  --valid-ratio 0.15 `
  --test-ratio 0.15 `
  --seed 42 `
  --complete-halves
```

Puis entraîne avec :

```powershell
python -m sportinsight.train --config configs/default.yaml
```

La configuration par défaut utilise `splits/train.txt` et `splits/valid.txt`. L’interface lit `splits/test.txt` pour proposer directement des matchs de test à analyser. Voir `docs/split_protocol.md`.

