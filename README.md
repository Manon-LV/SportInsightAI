# SportInsight AI

Système de détection automatique d'événements dans des matchs de football, basé sur un modèle de type dense anchor (CALF) entraîné sur SoccerNet.

---

## Architecture

```
sportinsight_final/
├── apps/
│   ├── api/                    # Backend FastAPI (port 8000)
│   │   ├── main.py             # Routes HTTP
│   │   ├── schemas.py          # Modèles Pydantic
│   │   ├── inference_service.py
│   │   ├── upload_service.py
│   │   ├── features_service.py
│   │   ├── match_service.py
│   │   ├── download_service.py
│   │   └── storage/            # Données persistées (runs, clips, uploads)
│   └── web/                    # Frontend Vue 3 + Quasar (port 9000)
│       └── src/
│           ├── pages/
│           │   ├── MainMenu.vue
│           │   └── AnalystRoom.vue
│           ├── components/
│           │   ├── ControlPanel.vue
│           │   ├── TimelineView.vue
│           │   ├── EventPanel.vue
│           │   ├── VideoUploader.vue
│           │   ├── VideoClipPreview.vue
│           │   ├── ReportPanel.vue
│           │   └── PerformancePanel.vue
│           └── services/
│               └── api.ts
├── src/sportinsight/           # Package Python
│   ├── model.py                # DenseAnchorSpotter (U-Net 1D + attention)
│   ├── infer.py                # Pipeline d'inférence
│   ├── data.py                 # Chargement des features SoccerNet
│   ├── train.py                # Entraînement
│   ├── losses.py               # CALF loss
│   ├── postprocess.py          # NMS et filtrage
│   └── metrics.py              # mAP SoccerNet
└── runs/                       # Checkpoints entraînés
    └── calf_17_slim_tdrop_sam/ # Modèle principal (17 classes)
```

---

## Modèle

**Architecture** : `DenseAnchorSpotter`

- Projection linéaire de l'espace des features (512 → 96)
- Temporal Dropout (p=0.5, masquage aléatoire à l'entraînement)
- U-Net 1D à 2 niveaux avec attention multi-têtes au bottleneck
- Deux têtes de sortie : classification (logits) et régression (offset temporel en secondes)

**Checkpoint** : `runs/calf_17_slim_tdrop_sam/best.pt`

**Classes détectées (17)** : Penalty, Kick-off, Goal, Substitution, Offside, Shots on target, Shots off target, Clearance, Ball out of play, Throw-in, Foul, Indirect free-kick, Direct free-kick, Corner, Yellow card, Red card, Yellow->red card

**Entrée** : features ResNET PCA512 à 2 fps — fichiers `1_ResNET_TF2_PCA512.npy` / `2_ResNET_TF2_PCA512.npy`

---

## Prérequis

- Python 3.10+
- Node.js 18+
- (Optionnel) FFmpeg pour la génération d'extraits vidéo

```bash
pip install -e sportinsight_final/
```

---

## Lancement

### Backend

```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload --port 8000
```

### Frontend

```bash
cd sportinsight_final/apps/web
npm install
npm run dev
# Accessible sur http://localhost:9000
```

---

## Utilisation

L'interface propose deux modes d'accès depuis le menu principal.

### Analyser un match SoccerNet

Sélectionner un répertoire de match contenant les fichiers features `.npy` et un checkpoint, puis lancer l'inférence. Les événements détectés s'affichent sur une timeline interactive. Si des fichiers vidéo `1.mkv` / `2.mkv` sont présents dans le répertoire, des extraits sont jouables directement depuis le panneau d'événements.

### Importer un match personnalisé

Deux sous-modes disponibles :

**Mode vidéo** : upload des deux mi-temps en MP4/MKV. Les features ResNET sont extraites automatiquement (nécessite un GPU ou un CPU puissant, ~5-15 min).

**Mode features** : upload direct des fichiers `.npy` pré-extraits. Les fichiers vidéo peuvent être ajoutés optionnellement pour la lecture dans l'interface.

---

## API REST

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | Statut du service |
| `GET` | `/matches` | Liste les matchs SoccerNet disponibles |
| `GET` | `/checkpoints` | Liste les checkpoints disponibles |
| `POST` | `/inference/run` | Lance une inférence |
| `GET` | `/runs/{id}/events` | Récupère les événements d'un run |
| `GET` | `/runs/{id}/summary` | Résumé d'un run |
| `POST` | `/upload/create` | Crée un job d'import |
| `POST` | `/upload/{id}/video/{half}` | Upload une vidéo (mi-temps 1 ou 2) |
| `POST` | `/upload/{id}/upload-features` | Upload un fichier `.npy` |
| `POST` | `/upload/{id}/finalize` | Finalise l'import vidéo |
| `POST` | `/upload/{id}/extract-features` | Extrait les features ResNET |
| `GET` | `/upload/{id}` | Statut d'un job d'import |
| `GET` | `/media/video` | Streaming de la vidéo d'une mi-temps |
| `GET` | `/media/clip` | Extrait vidéo autour d'un événement |
