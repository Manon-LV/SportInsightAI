# 🎬 Architecture et Flux de Travail - Import de Vidéos

## Vue d'ensemble

```
                          ┌─────────────────────┐
                          │   Votre Ordinateur  │
                          │                     │
                          │  ┌───────────────┐  │
                          │  │  Vidéo Match  │  │
                          │  │ (half1 + half2)  │
                          │  └───────────────┘  │
                          └──────────┬──────────┘
                                     │
                                     ▼
                     ┌───────────────────────────────┐
                     │   API FastAPI (port 8000)     │
                     └───────────────────────────────┘
                                     │
                ┌────────────────────┼────────────────────┐
                │                    │                    │
                ▼                    ▼                    ▼
          ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
          │   Upload     │    │  Features    │    │  Inference   │
          │   Service    │    │  Service     │    │  Service     │
          └──────────────┘    └──────────────┘    └──────────────┘
                │                    │                    │
                │ Vidéos             │ ResNET50           │ Model
                │ MP4/MKV            │ + GPU              │ Weights
                │                    │                    │
                ▼                    ▼                    ▼
        ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
        │ Storage/       │  │ 1.npy (3600f)  │  │ Détections     │
        │ uploads/       │  │ 2.npy (3600f)  │  │ d'événements   │
        │ Match/         │  └────────────────┘  │ (labels,       │
        │ 1.mp4, 2.mp4   │                      │ timestamps,    │
        └────────────────┘                      │ scores)        │
                                                 └────────────────┘
                                                         │
                                                         ▼
                                                  ┌──────────────┐
                                                  │  Résultats   │
                                                  │  JSON        │
                                                  └──────────────┘
```

---

## Flux de travail détaillé

```
┌─────────────────────────────────────────────────────────────────────┐
│                     WORKFLOW COMPLET                                 │
└─────────────────────────────────────────────────────────────────────┘

1. CLIENT (Python/cURL/Web)
   │
   └─> POST /upload/create
       └─> UploadService.create_job()
           └─> Génère: job_id = "upload_a1b2c3d4e5f6"
               État: uploading

2. CLIENT
   │
   ├─> POST /upload/{job_id}/video/1
   │   └─> UploadService.save_video_file(1, data)
   │       └─> Sauvegarde: storage/uploads/{job_id}/Match/1.mp4
   │           État: uploading
   │
   └─> POST /upload/{job_id}/video/2
       └─> UploadService.save_video_file(2, data)
           └─> Sauvegarde: storage/uploads/{job_id}/Match/2.mp4
               État: uploading

3. CLIENT
   │
   └─> POST /upload/{job_id}/finalize
       └─> UploadService.finalize_upload()
           ├─> Vérifie: 1.mp4 et 2.mp4 présents
           └─> État: processing → prêt pour features

4. CLIENT
   │
   └─> POST /upload/{job_id}/extract-features?fps=2.0
       └─> FeaturesService.extract_features_from_match_videos()
           ├─> Pour chaque vidéo:
           │   ├─> Extraction frames via FFmpeg
           │   │   └─> 3600 frames @ fps=2.0 pour 30 min vidéo
           │   │
           │   ├─> Chargement ResNET50 (ImageNet weights)
           │   │
           │   ├─> Pour chaque frame:
           │   │   ├─> Preprocessing (224x224, normalisation)
           │   │   ├─> Forward pass ResNET50
           │   │   └─> Extraction features (2048D)
           │   │
           │   └─> Sauvegarde: 1_ResNET_TF2_PCA512.npy
           │                   2_ResNET_TF2_PCA512.npy
           │
           └─> État: features_extracted

5. CLIENT
   │
   └─> POST /inference/run
       ├─> Match dir: storage/uploads/{job_id}/Match
       ├─> Checkpoint: runs/best.pt
       │
       └─> InferenceService.run_inference()
           ├─> Charge features .npy
           ├─> Charge model weights
           ├─> Pour chaque mi-temps:
           │   ├─> Détecte événements par fenêtrage
           │   ├─> NMS (Non-Maximum Suppression)
           │   └─> Filtrage par score threshold
           │
           └─> Retourne: events JSON
               ├─> label: "Goal", "Card", etc.
               ├─> timestamp: 1234.5 sec
               ├─> score: 0.95
               └─> ...
```

---

## Structure des données

### Job d'upload

```json
{
  "job_id": "upload_a1b2c3d4e5f6",
  "status": "processing",
  "match_name": "PSG vs Lyon",
  "match_dir": "storage/uploads/upload_a1b2c3d4e5f6/PSG vs Lyon",
  "half_1_path": "storage/uploads/.../1.mp4",
  "half_2_path": "storage/uploads/.../2.mp4",
  "features_status": "pending",
  "created_at": "2024-06-17T10:30:00Z",
  "updated_at": "2024-06-17T10:32:00Z",
  "message": "Upload terminé. Prêt à extraire les features."
}
```

### Événements détectés

```json
{
  "run_id": "run_xyz123",
  "events": [
    {
      "half": 1,
      "timestamp": 125.5,
      "gameTime": "02:05",
      "label": "Goal",
      "score": 0.98
    },
    {
      "half": 1,
      "timestamp": 234.2,
      "gameTime": "03:54",
      "label": "Yellow Card",
      "score": 0.87
    }
  ],
  "summary": {
    "event_count": 42,
    "counts_by_class": {
      "Goal": 2,
      "Yellow Card": 15,
      "Red Card": 1,
      "Substitution": 24
    }
  }
}
```

---

## Intégration avec le système existant

```
                    ┌──────────────────────────┐
                    │  Système existant         │
                    │  (SoccerNet download)     │
                    └──────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
    ┌──────────────────────┐    ┌──────────────────────┐
    │   Télécharger        │    │   Upload Custom      │
    │   depuis SoccerNet   │    │   Video (NOUVEAU)    │
    │                      │    │                      │
    │   data/SoccerNet/    │    │   storage/uploads/   │
    │   └─ match/          │    │   └─ upload_id/      │
    │      ├─ 1.mkv        │    │      └─ Match/       │
    │      ├─ 2.mkv        │    │         ├─ 1.mp4    │
    │      ├─ 1.npy        │    │         ├─ 2.mp4    │
    │      └─ 2.npy        │    │         ├─ 1.npy    │
    │                      │    │         └─ 2.npy    │
    └──────────────────────┘    └──────────────────────┘
                    │                         │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Inference Service      │
                    │  (identique)            │
                    └──────────────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  Résultats               │
                    │  (événements + scores)   │
                    └──────────────────────────┘
```

---

## Flux des données dans Features Service

```
Vidéo Input
    │
    ├─> FFmpeg extraction
    │   ├─> fps=2.0 → ~3600 frames pour 30 min vidéo
    │   └─> Sortie: JPEG frames
    │
    ├─> ResNET50 Processing
    │   ├─> Charge modèle (ImageNet weights)
    │   ├─> Pour chaque frame:
    │   │   ├─> PIL Image.open()
    │   │   ├─> Resize to 256x256
    │   │   ├─> CenterCrop to 224x224
    │   │   ├─> ToTensor() + normalisation
    │   │   ├─> Forward pass → Remove classification head
    │   │   └─> Extract 2048D features
    │   │
    │   └─> Stack to (3600, 2048)
    │
    └─> Sauvegarde
        └─> numpy.save() → 1_ResNET_TF2_PCA512.npy
```

---

## Parallélisme et optimization

### GPU vs CPU

```
┌─────────────────────────────────────────────────────────┐
│              Extraction Features (45 min vidéo)         │
├─────────────────────────────────────────────────────────┤
│  CPU (4 cores, 8GB)          │  25-30 minutes          │
│  CPU (8 cores, 16GB)         │  12-15 minutes          │
│  GPU (NVIDIA GTX 1080)       │  3-4 minutes            │
│  GPU (NVIDIA RTX 3090)       │  1-2 minutes            │
└─────────────────────────────────────────────────────────┘
```

### Optimisation FPS

```
┌─────────────────────────────────────────────────────────┐
│         Nombre de frames vs Temps d'extraction          │
├─────────────────────────────────────────────────────────┤
│  fps=0.5  (50 frames/min)    │  1800 frames  │  8 min  │
│  fps=2.0  (120 frames/min)   │  3600 frames  │ 15 min  │
│  fps=5.0  (300 frames/min)   │  9000 frames  │ 30 min  │
└─────────────────────────────────────────────────────────┘
```

---

## Gestion des erreurs

```
┌─────────────────────────────────────────────────────────┐
│              Pipeline de gestion d'erreurs              │
└─────────────────────────────────────────────────────────┘

Upload
  ├─> Erreur: Fichier introuvable
  │   └─> HTTP 404 + message
  │
  ├─> Erreur: Vidéo corrompue
  │   └─> Sauvegarde partiellement, state=error
  │
  └─> Erreur: Finalize sans les 2 mi-temps
      └─> HTTP 400 + validation error

Features Extraction
  ├─> Erreur: FFmpeg manquant
  │   └─> HTTP 501 + Installation instructions
  │
  ├─> Erreur: GPU out of memory
  │   └─> Fallback to CPU, state=processing
  │
  ├─> Erreur: Frame extraction failure
  │   └─> Skip frame, continue with next
  │
  └─> Erreur: Model loading
      └─> HTTP 500 + Check model file

Inference
  ├─> Erreur: Features .npy missing
  │   └─> HTTP 404 + Extract first
  │
  ├─> Erreur: Model checkpoint missing
  │   └─> HTTP 404 + List available checkpoints
  │
  └─> Erreur: Invalid parameters
      └─> HTTP 400 + Validation error
```

---

## Sécurité et limitations

### Limitations actuelles

- 📁 Max 2GB par upload (configurable)
- ⏱️ Timeout 10 min pour extraction
- 💾 Stockage local (pas de réplication)
- 👤 Pas d'authentification (à ajouter)

### Recommandations pour production

- ✅ Ajouter authentification JWT
- ✅ Implémenter quotas utilisateur
- ✅ Ajouter logging détaillé
- ✅ Utiliser base de données (PostgreSQL)
- ✅ Chiffrer les vidéos sensibles
- ✅ Implémenter purge automatique
- ✅ Ajouter monitoring/alertes

---

## Déploiement

### Local (Développement)

```bash
uvicorn apps.api.main:app --reload --port 8000
```

### Docker

```dockerfile
FROM python:3.10
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
RUN apt-get update && apt-get install -y ffmpeg
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0"]
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sportinsight-api
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: api
        image: sportinsight:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "4Gi"
            cpu: "2"
          limits:
            memory: "8Gi"
            cpu: "4"
```

---

## Monitoring et logs

### Logs recommandés

```python
logger.info(f"Job {job_id} créé pour match {match_name}")
logger.info(f"Vidéo {half} uploadée: {size} bytes")
logger.info(f"Features extraction started: fps={fps}, device={device}")
logger.warning(f"GPU memory low, using CPU")
logger.error(f"Features extraction failed: {error}")
```

### Métriques à surveiller

- Nombre de jobs actifs
- Temps d'extraction moyen
- Taux de réussite
- Utilisation GPU/CPU
- Espace disque disponible
