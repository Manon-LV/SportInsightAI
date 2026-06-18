# 🎬 Import et Analyse de Vidéos Personnalisées

Ce guide explique comment importer et analyser vos propres vidéos de matchs de football avec SportInsight AI.

## 📋 Table des matières

1. [Installation](#installation)
2. [Démarrer l'API](#démarrer-lapi)
3. [Workflow complet](#workflow-complet)
4. [Endpoints détaillés](#endpoints-détaillés)
5. [Exemples](#exemples)
6. [Troubleshooting](#troubleshooting)

---

## Installation

### Prérequis

- **Python 3.8+**
- **FFmpeg** (pour l'extraction des frames et la génération de clips)
- **GPU optionnel** (CUDA pour accélérer l'extraction de features)

### Installation de FFmpeg

**Windows:**
```powershell
# Via Chocolatey
choco install ffmpeg

# Ou télécharger depuis: https://ffmpeg.org/download.html
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### Installation des dépendances Python

```bash
cd sportinsight_final
pip install -r requirements.txt

# Optionnel: Pour l'accélération GPU
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

---

## Démarrer l'API

### Mode développement (avec rechargement automatique)

```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Mode production

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Vérifiez que l'API est démarrée:
```bash
curl http://localhost:8000/health
```

---

## Workflow Complet

### Étapes principales

```
1. Créer un job d'upload
        ↓
2. Upload vidéo mi-temps 1
        ↓
3. Upload vidéo mi-temps 2
        ↓
4. Finaliser l'upload
        ↓
5. Extraire les features ResNET
        ↓
6. Lancer l'inférence (détection d'événements)
        ↓
7. Afficher les résultats
```

### Via le script Python

```bash
python apps/api/upload_example.py \
    --match-name "PSG vs OM" \
    --video-1 /path/to/half1.mp4 \
    --video-2 /path/to/half2.mp4 \
    --checkpoint runs/best_model/best.pt \
    --fps 2.0 \
    --device auto
```

### Via cURL (étape par étape)

#### 1. Créer un job

```bash
curl -X POST "http://localhost:8000/upload/create" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "match_name=My Match"
```

Réponse:
```json
{
  "job_id": "upload_a1b2c3d4e5f6",
  "message": "Job créé pour le match: My Match"
}
```

#### 2. Upload mi-temps 1

```bash
curl -X POST "http://localhost:8000/upload/upload_a1b2c3d4e5f6/video/1" \
    -F "file=@/path/to/half1.mp4"
```

#### 3. Upload mi-temps 2

```bash
curl -X POST "http://localhost:8000/upload/upload_a1b2c3d4e5f6/video/2" \
    -F "file=@/path/to/half2.mp4"
```

#### 4. Finaliser l'upload

```bash
curl -X POST "http://localhost:8000/upload/upload_a1b2c3d4e5f6/finalize"
```

Réponse:
```json
{
  "job_id": "upload_a1b2c3d4e5f6",
  "status": "processing",
  "match_dir": "/path/to/storage/uploads/upload_a1b2c3d4e5f6/My Match",
  "message": "Upload terminé. Prêt à extraire les features."
}
```

#### 5. Extraire les features (⏱️ 5-15 min selon la taille)

```bash
curl -X POST "http://localhost:8000/upload/upload_a1b2c3d4e5f6/extract-features" \
    -G \
    -d "fps=2.0" \
    -d "device=auto"
```

#### 6. Lancer l'inférence

```bash
curl -X POST "http://localhost:8000/inference/run" \
    -H "Content-Type: application/json" \
    -d '{
      "match_dir": "/path/to/storage/uploads/upload_a1b2c3d4e5f6/My Match",
      "checkpoint": "runs/best_model/best.pt",
      "half": "both",
      "score_threshold": 0.30
    }'
```

#### 7. Récupérer l'état du job

```bash
curl "http://localhost:8000/upload/upload_a1b2c3d4e5f6"
```

---

## Endpoints Détaillés

### Création d'un job

**POST** `/upload/create`

Crée un nouveau job d'upload.

**Paramètres:**
- `match_name` (string, required): Nom du match

**Réponse:**
```json
{
  "job_id": "upload_...",
  "message": "Job créé pour le match: ..."
}
```

---

### Upload d'une vidéo

**POST** `/upload/{job_id}/video/{half}`

Upload la vidéo pour une mi-temps.

**Paramètres:**
- `job_id` (path, required): ID du job
- `half` (path, required): 1 ou 2
- `file` (file, required): Fichier vidéo

**Formats supportés:** MP4, MKV, WebM, MOV, AVI

**Réponse:**
```json
{
  "job_id": "upload_...",
  "half": 1,
  "path": "/path/to/video",
  "size": 1024000000
}
```

---

### Finalisation

**POST** `/upload/{job_id}/finalize`

Finalise l'upload. Les deux mi-temps doivent être présentes.

**Réponse:** Voir [UploadStatus](#uploadstatus)

---

### Extraction de features

**POST** `/upload/{job_id}/extract-features`

Lance l'extraction des features ResNET.

**Paramètres de query:**
- `fps` (float, optional): Frames par seconde (0.5-30.0, défaut: 2.0)
- `device` (string, optional): Device (auto, cpu, cuda)

**Note:** Cette opération peut prendre 5-15 minutes selon:
- La durée totale de la vidéo
- Le nombre de frames à traiter (dépend de fps)
- La puissance du GPU/CPU

**Réponse:**
```json
{
  "job_id": "upload_...",
  "status": "features_extracted",
  "match_dir": "/path/to/match",
  "halves": {
    "1": {
      "status": "success",
      "video_path": "...",
      "features_path": "...",
      "num_frames": 3600,
      "feature_shape": [3600, 2048]
    },
    "2": { ... }
  },
  "message": "Features extraites avec succès..."
}
```

---

### État du job

**GET** `/upload/{job_id}`

Récupère l'état complet du job.

**Réponse:** Voir [UploadStatus](#uploadstatus)

---

### Lister tous les jobs

**GET** `/upload`

Liste tous les jobs d'upload.

**Réponse:**
```json
[
  { UploadStatus },
  { UploadStatus }
]
```

---

### Supprimer un job

**DELETE** `/upload/{job_id}`

Supprime le job et ses fichiers.

**Réponse:**
```json
{
  "message": "Job supprimé: upload_..."
}
```

---

## Modèles de données

### UploadStatus

```json
{
  "job_id": "upload_a1b2c3d4e5f6",
  "status": "processing",
  "created_at": "2024-01-15T10:30:00+00:00",
  "updated_at": "2024-01-15T10:35:00+00:00",
  "match_name": "PSG vs OM",
  "half_1_path": "/path/to/1.mp4",
  "half_2_path": "/path/to/2.mp4",
  "half_1_size": 1024000000,
  "half_2_size": 950000000,
  "features_status": "pending",
  "match_dir": "/path/to/storage/uploads/upload_.../PSG vs OM",
  "message": "Upload terminé. Prêt à extraire les features.",
  "error": null
}
```

---

## Exemples

### Exemple 1: Script Python complet

```python
from apps.api.upload_example import SportInsightUploadClient

client = SportInsightUploadClient("http://localhost:8000")

# Upload et analyse complète
result = client.upload_and_analyze(
    match_name="PSG vs Lyon",
    video_1_path="/videos/half1.mp4",
    video_2_path="/videos/half2.mp4",
    checkpoint="runs/best_model/best.pt",
    half="both",
    fps=2.0,
    device="cuda"
)

# Afficher les événements détectés
for event in result["events"]:
    print(f"{event['gameTime']}: {event['label']} (confidence: {event['score']:.2%})")
```

### Exemple 2: Via Python requests

```python
import requests

base_url = "http://localhost:8000"

# 1. Créer job
job_resp = requests.post(f"{base_url}/upload/create", data={"match_name": "My Match"})
job_id = job_resp.json()["job_id"]

# 2. Upload vidéos
with open("half1.mp4", "rb") as f:
    requests.post(f"{base_url}/upload/{job_id}/video/1", files={"file": f})
with open("half2.mp4", "rb") as f:
    requests.post(f"{base_url}/upload/{job_id}/video/2", files={"file": f})

# 3. Finaliser
requests.post(f"{base_url}/upload/{job_id}/finalize")

# 4. Extraire features
features = requests.post(f"{base_url}/upload/{job_id}/extract-features", 
                         params={"fps": 2.0}).json()

# 5. Inférence
match_dir = features["match_dir"]
inference = requests.post(f"{base_url}/inference/run", json={
    "match_dir": match_dir,
    "checkpoint": "runs/best_model/best.pt"
}).json()

print(f"Events found: {len(inference['events'])}")
```

### Exemple 3: Intégration avec UI web

```typescript
// Vue.js / TypeScript
async function uploadAndAnalyze(matchName: string, video1: File, video2: File) {
  const baseUrl = 'http://localhost:8000';
  
  // Créer job
  const jobRes = await fetch(`${baseUrl}/upload/create`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `match_name=${encodeURIComponent(matchName)}`
  });
  const { job_id } = await jobRes.json();
  
  // Upload videos
  for (let half = 1; half <= 2; half++) {
    const formData = new FormData();
    formData.append('file', half === 1 ? video1 : video2);
    
    await fetch(`${baseUrl}/upload/${job_id}/video/${half}`, {
      method: 'POST',
      body: formData
    });
  }
  
  // Finaliser
  await fetch(`${baseUrl}/upload/${job_id}/finalize`, { method: 'POST' });
  
  // Extraire features
  const featuresRes = await fetch(`${baseUrl}/upload/${job_id}/extract-features`, {
    method: 'POST'
  });
  
  return job_id;
}
```

---

## Troubleshooting

### ❌ Erreur: "ffmpeg est introuvable"

**Solution:**
```bash
# Windows
choco install ffmpeg

# Ou ajouter ffmpeg au PATH manuellement
# Puis redémarrer le terminal/IDE
```

### ❌ Erreur: "PyTorch/torchvision manquantes"

**Solution:**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### ❌ Erreur: "Impossible de se connecter à l'API"

**Solution:**
```bash
# Vérifier que l'API est démarrée
curl http://localhost:8000/health

# Si non, lancer l'API
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

### ⏱️ L'extraction de features prend trop longtemps

**Solutions:**
1. **Augmenter fps** (moins de frames):
   ```bash
   curl -X POST "http://localhost:8000/upload/{job_id}/extract-features" \
       -G -d "fps=0.5"  # Au lieu de 2.0
   ```

2. **Utiliser le GPU** (si disponible):
   ```bash
   curl -X POST "http://localhost:8000/upload/{job_id}/extract-features" \
       -G -d "device=cuda"
   ```

### 💾 Les fichiers uploadés sont trop volumineux

**Solutions:**
1. **Compresser la vidéo avant l'upload:**
   ```bash
   ffmpeg -i input.mp4 -vf scale=1280:720 -crf 23 output.mp4
   ```

2. **Réduire la qualité pendant l'extraction:**
   ```bash
   # Les frames seront re-scalées à 224x224 de toute façon
   # Donc uploader en 720p est suffisant
   ```

### 🎯 Les résultats de détection ne sont pas bons

**Solutions:**
1. **Ajuster le seuil de confiance:**
   ```bash
   curl -X POST "http://localhost:8000/inference/run" \
       -H "Content-Type: application/json" \
       -d '{
         "match_dir": "...",
         "checkpoint": "...",
         "score_threshold": 0.25
       }'
   ```

2. **Utiliser un meilleur checkpoint:**
   ```bash
   # Liste les checkpoints disponibles
   curl http://localhost:8000/checkpoints
   ```

---

## Performance

### Temps estimés

| Opération | Durée | Facteurs |
|-----------|-------|----------|
| Upload (100 MB) | 10-30s | Vitesse internet |
| Extraction features (45 min vidéo) | 5-15 min | GPU/CPU, fps |
| Inférence | 30s-2 min | Nombre de frames |

### Optimisation

| Paramètre | Valeur | Effet |
|-----------|--------|-------|
| fps | 2.0 | Équilibre qualité/vitesse |
| fps | 0.5 | Plus rapide, moins détaillé |
| fps | 5.0 | Plus lent, plus détaillé |
| device | cuda | 5-10x plus rapide (si GPU) |
| device | cpu | Compatible partout |

---

## Support

Pour des problèmes ou questions:
1. Vérifier les logs de l'API: `uvicorn apps.api.main:app --reload`
2. Vérifier les fichiers uploadés: `apps/api/storage/uploads/`
3. Ouvrir une issue sur le projet

