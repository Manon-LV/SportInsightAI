# 📋 Architecture Complète - SportInsight AI

## 🏗️ Vue d'ensemble globale

```
┌─────────────────────────────────────────────────────────┐
│                   Client Web (Vue 3)                    │
│  - MainMenu (Navigation)                                │
│  - AnalystRoom (Analyse)                                │
│  - VideoUploader (Upload)                               │
│  - Timeline (Visualisation)                             │
│  - EventList (Résultats)                                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP/REST
                       ▼
┌─────────────────────────────────────────────────────────┐
│                 FastAPI Backend                         │
│                  (Port 8000)                            │
├─────────────────────────────────────────────────────────┤
│ • API Routes (7 endpoints upload + 3 analysis)          │
│ • Job Management (UploadService)                        │
│ • Video Processing (FeaturesService)                    │
│ • Model Inference (InferenceService)                    │
│ • File Storage Management                               │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
    ┌────────┐  ┌────────────┐  ┌──────────┐
    │ FFmpeg │  │ PyTorch    │  │ Storage  │
    │        │  │ ResNET50   │  │ Local FS │
    │ Frames │  │ Features   │  │ Jobs     │
    └────────┘  └────────────┘  └──────────┘
```

## 📂 Structure des dossiers

```
sportinsight_final/
├── apps/
│   ├── api/                          # Backend FastAPI
│   │   ├── main.py                   # Application principale
│   │   ├── schemas.py                # Modèles Pydantic
│   │   ├── upload_service.py         # Gestion des uploads
│   │   ├── features_service.py       # Extraction de features
│   │   ├── inference_service.py      # Inférence des modèles
│   │   ├── match_service.py          # Gestion des matchs
│   │   ├── download_service.py       # Téléchargement
│   │   ├── storage/                  # Dossier d'uploads
│   │   │   └── uploads/
│   │   │       └── {job_id}/
│   │   │           └── {match_name}/
│   │   │               ├── 1.mp4
│   │   │               ├── 2.mp4
│   │   │               ├── 1_ResNET_TF2_PCA512.npy
│   │   │               └── 2_ResNET_TF2_PCA512.npy
│   │   └── ...
│   │
│   └── web/                          # Frontend Vue 3
│       ├── src/
│       │   ├── components/
│       │   │   ├── VideoUploader.vue  # Upload UI
│       │   │   ├── Timeline.vue       # Timeline
│       │   │   ├── EventList.vue      # Événements
│       │   │   └── ...
│       │   ├── pages/
│       │   │   ├── MainMenu.vue       # Menu principal
│       │   │   ├── AnalystRoom.vue    # Analyse
│       │   │   └── ...
│       │   ├── services/
│       │   │   └── api.ts             # Appels API
│       │   ├── types/
│       │   │   └── predictions.ts     # Types TS
│       │   ├── App.vue                # Entrée
│       │   └── main.ts                # Bootstrap
│       ├── .env.example               # Config exemple
│       ├── package.json               # Dépendances
│       ├── vite.config.ts             # Config Vite
│       ├── README_WEB.md              # Doc web
│       ├── WEB_QUICKSTART.md          # Quickstart
│       └── WEB_INTERFACE_GUIDE.md     # Guide détaillé
│
├── configs/                          # Fichiers de config YAML
├── data/                             # Données SoccerNet
├── runs/                             # Résultats d'entraînement
├── checkpoints/                      # Modèles pré-entraînés
├── splits/                           # Train/test/valid splits
│
├── README.md                         # Doc principale
├── QUICK_START.md                    # Démarrage rapide
├── INDEX.md                          # Index documentation
└── requirements.txt                  # Dépendances Python
```

## 🔄 Workflows

### Workflow 1: Upload et analyse

```
1. Menu Principal
   ├─ Utilisateur clique "Uploader une vidéo"
   └─ Redirection vers VideoUploader.vue

2. VideoUploader.vue
   ├─ Saisie du nom du match
   ├─ Drag-and-drop mi-temps 1 et 2
   ├─ Sélection du checkpoint
   └─ Clique "Uploader"

3. Service API (api.ts)
   ├─ createUploadJob(matchName)
   ├─ uploadVideo(jobId, 1, file1)
   ├─ uploadVideo(jobId, 2, file2)
   ├─ finalizeUpload(jobId)
   └─ extractFeatures(jobId)

4. Backend (main.py)
   ├─ POST /upload/create
   │  └─ UploadService.create_upload_job()
   ├─ POST /upload/{job_id}/video/{half}
   │  └─ UploadService.save_video_file()
   ├─ POST /upload/{job_id}/finalize
   │  └─ UploadService.finalize_upload()
   └─ POST /upload/{job_id}/extract-features
      └─ FeaturesService.extract_features_from_match_videos()

5. Extraction Features
   ├─ FFmpeg: video → frames (fps=2)
   ├─ PyTorch: Load ResNET50
   ├─ Loop sur frames
   ├─ 2048D feature vectors
   ├─ Sauvegarde .npy
   └─ Affichage "Prêt pour analyse"

6. AnalystRoom.vue
   ├─ Affiche le match
   ├─ Match dir = /storage/uploads/{job_id}/{match_name}
   ├─ Lancement inférence (POST /inference/run)
   ├─ Affichage Timeline
   └─ Affichage EventList

7. Visualisation
   ├─ Timeline interactive
   ├─ Événements codés par couleur
   ├─ Liste détaillée
   └─ Export possible
```

### Workflow 2: Analyse SoccerNet

```
1. Menu Principal
   ├─ Utilisateur clique "Analyser un match"
   └─ Redirection vers AnalystRoom.vue

2. AnalystRoom.vue
   ├─ GET /splits → Liste des splits
   ├─ GET /splits/{split}/matches → Liste des matches
   ├─ Utilisateur sélectionne un match
   └─ Sélectionne un checkpoint

3. Service API (api.ts)
   ├─ runInference(request)
   └─ getVideoAvailability(matchDir)

4. Backend (main.py)
   ├─ POST /inference/run
   │  └─ InferenceService.run_inference()
   └─ GET /media/video → Streaming vidéo

5. Inférence
   ├─ Charge features (.npy)
   ├─ Load checkpoint (PyTorch)
   ├─ Inférence (batch processing)
   ├─ Post-processing (NMS, etc.)
   ├─ Détection d'événements
   └─ Retour JSON événements

6. Visualisation
   ├─ Timeline interactive
   ├─ Vidéo 4K avec événements superposés
   ├─ EventList avec détails
   └─ Export clips possibles
```

## 🔌 API Routes

### Upload Routes
```
POST   /upload/create                           → job_id
POST   /upload/{job_id}/video/{half}            → save video
POST   /upload/{job_id}/finalize                → validate
POST   /upload/{job_id}/extract-features        → extract
GET    /upload/{job_id}                         → status
DELETE /upload/{job_id}                         → cleanup
```

### Analysis Routes
```
POST   /inference/run                           → detect events
GET    /media/video                             → stream video
GET    /media/clip                              → export clip
GET    /media/video/availability                → check files
```

### Data Routes
```
GET    /splits                                  → list splits
GET    /splits/{split}/matches                  → list matches
GET    /splits/integrity                        → validate data
GET    /checkpoints                             → list models
```

### Health
```
GET    /health                                  → {status, service}
```

## 📊 Data Models

### UploadStatus
```json
{
  "job_id": "uuid",
  "status": "uploading|processing|done|error",
  "match_name": "PSG vs Lyon",
  "half_1_path": "/storage/uploads/uuid/PSG vs Lyon/1.mp4",
  "half_2_path": "/storage/uploads/uuid/PSG vs Lyon/2.mp4",
  "half_1_size": 1024000000,
  "half_2_size": 1024000000,
  "features_status": "pending|extracting|done|error",
  "match_dir": "/storage/uploads/uuid/PSG vs Lyon",
  "message": "Features extracted successfully",
  "error": null
}
```

### EventPrediction
```json
{
  "event_type": "Shot",
  "timestamp": 45.5,
  "confidence": 0.95,
  "half": 1,
  "frame": 91,
  "coordinates": [640, 360]
}
```

### InferenceRequest
```json
{
  "match_dir": "/data/SoccerNet/england_epl/...",
  "checkpoint": "best",
  "fps": 2.0,
  "device": "auto"
}
```

### InferenceResponse
```json
{
  "match_dir": "/data/SoccerNet/england_epl/...",
  "half_1": [{"event_type": "...", ...}, ...],
  "half_2": [{"event_type": "...", ...}, ...],
  "processing_time": 25.3
}
```

## 🔐 Storage Structure

```
storage/
└── uploads/
    └── {uuid}/                          # Job ID
        └── {match_name}/                # Match Name
            ├── 1.mp4                    # Original video
            ├── 2.mp4                    # Original video
            ├── 1_ResNET_TF2_PCA512.npy # Features half 1
            ├── 2_ResNET_TF2_PCA512.npy # Features half 2
            └── metadata.json            # Job metadata
```

## 🛠️ Technologies utilisées

### Frontend
- **Vue.js 3**: Framework réactif
- **TypeScript**: Typage statique
- **Quasar**: Composants UI Material
- **Vite**: Bundler ultra-rapide

### Backend
- **FastAPI**: Framework Web async
- **Pydantic**: Validation données
- **PyTorch**: Deep Learning
- **FFmpeg**: Traitement vidéo
- **NumPy**: Array processing

### Storage
- **FileSystem**: Local storage
- **JSON**: Métadonnées
- **NPY**: Features vectors

## 🚀 Déploiement

### Développement
```bash
# Terminal 1: API
cd sportinsight_final
uvicorn apps.api.main:app --reload

# Terminal 2: Web
cd sportinsight_final/apps/web
npm run dev

# Accès: http://localhost:5173
```

### Production
```bash
# Build frontend
cd apps/web && npm run build

# API avec Gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker apps.api.main:app

# Serve frontend avec Nginx
# (voir configuration Nginx)
```

### Docker
```bash
docker-compose up
# http://localhost:3000
```

## 📈 Performance

| Opération | Temps | Notes |
|-----------|-------|-------|
| Chargement page | < 2s | Frontend |
| API health | < 50ms | Backend |
| Upload 100MB | 10-30s | Réseau |
| Extraction features | 3-30min | GPU/CPU |
| Inférence | 5-10s | Batch |
| Timeline render | < 100ms | UI |

## 🔄 CI/CD Pipeline (suggéré)

```
1. Git Push
   ↓
2. Test Backend
   ├─ pytest
   ├─ linting
   └─ type checking
   ↓
3. Test Frontend
   ├─ npm test
   ├─ linting
   └─ build check
   ↓
4. Build Docker
   ├─ Backend image
   └─ Frontend image
   ↓
5. Deploy
   ├─ Staging
   └─ Production
```

## 🎓 Exemples d'utilisation

### Python CLI
```python
import requests

API = "http://localhost:8000"

# Créer job
job = requests.post(f"{API}/upload/create", 
                   data={"match_name": "PSG vs Lyon"})
job_id = job.json()["job_id"]

# Upload vidéos
with open("halftime1.mp4", "rb") as f:
    requests.post(f"{API}/upload/{job_id}/video/1",
                 files={"file": f})

# Extraire features
requests.post(f"{API}/upload/{job_id}/extract-features")

# Analyser
result = requests.post(f"{API}/inference/run",
                      json={"match_dir": f"storage/uploads/{job_id}/...",
                           "checkpoint": "best"})

print(result.json())
```

### Vue Component
```vue
<template>
  <div>
    <VideoUploader @analyze="onAnalyze" />
  </div>
</template>

<script setup>
import { uploadVideo, extractFeatures } from '@/services/api'

async function onAnalyze(data) {
  console.log("Analyzing:", data.match_dir)
}
</script>
```

## 📚 Documentation complète

- [README.md](README.md) - Guide principal
- [QUICK_START.md](QUICK_START.md) - Démarrage rapide
- [apps/web/README_WEB.md](apps/web/README_WEB.md) - Web détaillé
- [apps/web/WEB_QUICKSTART.md](apps/web/WEB_QUICKSTART.md) - Web quickstart
- [apps/web/WEB_INTERFACE_GUIDE.md](apps/web/WEB_INTERFACE_GUIDE.md) - Guide interface

## 🔗 Ressources

- [Vue.js 3](https://vuejs.org/)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Quasar](https://quasar.dev/)
- [PyTorch](https://pytorch.org/)
- [SoccerNet](https://www.soccer-net.org/)

---

**Status:** ✅ Production-ready  
**Dernière mise à jour:** 2024-06-17  
**Version:** 1.0.0
