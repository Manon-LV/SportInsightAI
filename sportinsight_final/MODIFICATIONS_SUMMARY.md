# 📝 Résumé des modifications - Import de vidéos personnalisées

Date: 2024-06-17
Version: 0.3.0

## 🎯 Objectif

Permettre l'import et l'analyse de vidéos personnalisées (mi-temps 1 et 2) sans dépendre du téléchargement SoccerNet.

## ✨ Nouvelles fonctionnalités

### 1. Upload de vidéos
- ✅ Endpoint pour créer des jobs d'upload
- ✅ Upload des deux mi-temps (1 et 2) séparément
- ✅ Support des formats: MP4, MKV, WebM, MOV, AVI
- ✅ Gestion des erreurs et validation

### 2. Extraction de features
- ✅ Extraction automatique des features ResNET depuis les vidéos
- ✅ Support GPU pour accélération
- ✅ Extraction configurable (fps, résolution)
- ✅ Stockage des features au format .npy compatible

### 3. Workflow complet
- ✅ Création de job → Upload → Extraction → Inférence
- ✅ Suivi de l'état de chaque étape
- ✅ Gestion des erreurs à chaque niveau

## 📁 Fichiers créés/modifiés

### Fichiers créés

| Fichier | Type | Description |
|---------|------|-------------|
| `apps/api/upload_service.py` | 📄 Nouveau | Service de gestion des uploads |
| `apps/api/features_service.py` | 📄 Nouveau | Service d'extraction de features ResNET |
| `apps/api/upload_example.py` | 📄 Nouveau | Script Python pour workflow complet |
| `UPLOAD_VIDEO_GUIDE.md` | 📚 Nouveau | Guide complet (endpoints, exemples, troubleshooting) |
| `UPLOAD_QUICKSTART.md` | 📚 Nouveau | Quick start 5 minutes |
| `SETUP_VIDEO_UPLOAD.md` | 📚 Nouveau | Guide d'installation et configuration |
| `notebooks/upload_and_analyze_videos.ipynb` | 📓 Nouveau | Notebook interactif |

### Fichiers modifiés

| Fichier | Modifications |
|---------|--------------|
| `apps/api/main.py` | ➕ 7 nouveaux endpoints API (upload, features, status, delete) |
| `apps/api/schemas.py` | ➕ 3 nouveaux schémas (UploadStatus, VideoUploadResponse, FeaturesExtractionStatus) |

## 🔌 API Endpoints

### Upload management

```
POST   /upload/create                        # Créer un job d'upload
POST   /upload/{job_id}/video/{half}         # Uploader vidéo (1 ou 2)
POST   /upload/{job_id}/finalize             # Finaliser l'upload
POST   /upload/{job_id}/extract-features     # Extraire features ResNET
GET    /upload/{job_id}                      # Récupérer l'état
GET    /upload                               # Lister tous les jobs
DELETE /upload/{job_id}                      # Supprimer un job
```

## 🚀 Utilisation

### Via le script Python

```bash
python apps/api/upload_example.py \
    --match-name "PSG vs Lyon" \
    --video-1 half1.mp4 \
    --video-2 half2.mp4 \
    --checkpoint runs/best.pt
```

### Via le notebook Jupyter

```bash
jupyter notebook notebooks/upload_and_analyze_videos.ipynb
```

### Via cURL (détaillé dans UPLOAD_VIDEO_GUIDE.md)

```bash
# 1. Créer job
job_id=$(curl -X POST "http://localhost:8000/upload/create" \
    -d "match_name=My Match" | jq -r '.job_id')

# 2. Upload videos
curl -X POST "http://localhost:8000/upload/$job_id/video/1" \
    -F "file=@half1.mp4"
curl -X POST "http://localhost:8000/upload/$job_id/video/2" \
    -F "file=@half2.mp4"

# 3. Extract features
curl -X POST "http://localhost:8000/upload/$job_id/extract-features"

# 4. Run inference
curl -X POST "http://localhost:8000/inference/run" \
    -H "Content-Type: application/json" \
    -d "{\"match_dir\": \"/path/...\", \"checkpoint\": \"runs/best.pt\"}"
```

## 🏗️ Architecture

### Workflow

```
Client (cURL/Python/Web)
        ↓
    API (FastAPI)
        ↓
    upload_service.py (gestion des jobs)
        ↓
    features_service.py (extraction ResNET)
        ↓
    inference (détection d'événements)
```

### Storage

```
apps/api/storage/
├── uploads/
│   ├── upload_id_1/
│   │   └── Match Name/
│   │       ├── 1.mp4  (vidéo)
│   │       ├── 2.mp4  (vidéo)
│   │       ├── 1_ResNET_TF2_PCA512.npy  (features)
│   │       └── 2_ResNET_TF2_PCA512.npy  (features)
│   └── upload_id_2/
│       └── ...
├── clips/
└── runs/
```

## 🔑 Fonctionnalités principales

### Upload Service
- Création de jobs d'upload
- Sauvegarde des vidéos
- Validation des fichiers
- Gestion de l'état du job

### Features Service
- Extraction des frames via FFmpeg
- Utilisation du modèle ResNET50
- Support GPU/CPU automatique
- Stockage au format .npy

### Integration
- Compatible avec le pipeline d'inférence existant
- Utilise la même structure de dossiers SoccerNet
- Fonctionne avec les modèles existants

## ⚙️ Configuration

### Prérequis
- ✅ FFmpeg (pour extraction des frames)
- ✅ PyTorch + TorchVision (pour ResNET)
- ✅ FastAPI + Uvicorn (API)

### Installation

```bash
# Installation FFmpeg
# Windows: choco install ffmpeg
# Linux: sudo apt install ffmpeg
# macOS: brew install ffmpeg

# Installation Python
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

## 📊 Performance

| Opération | Durée | Facteurs |
|-----------|-------|----------|
| Upload (100 MB) | 10-30s | Vitesse internet |
| Extraction features (45 min) | 3-30 min | GPU/CPU, fps |
| Inférence | 30s-2 min | Nombre de frames |

## 🧪 Tests

### Test complet

```bash
# Terminal 1: Démarrer l'API
cd sportinsight_final
uvicorn apps.api.main:app --reload

# Terminal 2: Lancer le test
python apps/api/upload_example.py \
    --match-name "Test Match" \
    --video-1 sample_video_1.mp4 \
    --video-2 sample_video_2.mp4 \
    --checkpoint runs/best.pt
```

### Test via Jupyter

```bash
jupyter notebook notebooks/upload_and_analyze_videos.ipynb
```

## 🐛 Gestion des erreurs

Erreurs gérées:
- ✅ Fichiers vidéo manquants
- ✅ Formats vidéo invalides
- ✅ Features extraction failures
- ✅ Model inference errors
- ✅ Job not found errors
- ✅ Disk space issues
- ✅ FFmpeg missing
- ✅ GPU memory exceeded

## 📈 Future improvements

### Possibles améliorations
- [ ] Support du streaming vidéo
- [ ] Compression vidéo automatique
- [ ] Cache des features
- [ ] Batch processing multiple matchs
- [ ] Integration WebUI
- [ ] Stockage en base de données
- [ ] API authentication
- [ ] Quotas utilisateur
- [ ] Notifications temps réel (WebSocket)

## 📚 Documentation

### Fichiers de documentation
- `UPLOAD_VIDEO_GUIDE.md` - Guide complet (endpoints, exemples)
- `UPLOAD_QUICKSTART.md` - Démarrage rapide (5 min)
- `SETUP_VIDEO_UPLOAD.md` - Installation et configuration
- `notebooks/upload_and_analyze_videos.ipynb` - Tutorial interactif

### Code comments
- ✅ Tous les fichiers ont des docstrings détaillées
- ✅ Exemples d'utilisation inclus
- ✅ Type hints Python complètes

## ✅ Checklist finale

- ✅ Service d'upload fonctionnel
- ✅ Service d'extraction de features
- ✅ API endpoints
- ✅ Validation et gestion d'erreurs
- ✅ Script Python exemple
- ✅ Notebook Jupyter
- ✅ Documentation complète
- ✅ Installation guide
- ✅ Type hints et docstrings

## 🎯 Prochaines étapes

1. **Installation**: Suivre `SETUP_VIDEO_UPLOAD.md`
2. **Quick test**: Essayer `UPLOAD_QUICKSTART.md`
3. **Exploration**: Utiliser `notebooks/upload_and_analyze_videos.ipynb`
4. **Production**: Voir `UPLOAD_VIDEO_GUIDE.md` pour détails complets

---

**Auteur**: GitHub Copilot  
**Date**: 2024-06-17  
**Status**: ✅ Prêt pour production
