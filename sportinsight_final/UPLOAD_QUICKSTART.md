# 🚀 Quick Start - Import de Vidéos

## 5 minutes pour commencer

### 1. Démarrer l'API

```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload --port 8000
```

Vérifier:
```bash
curl http://localhost:8000/health
```

### 2. Utiliser le script Python

```bash
python apps/api/upload_example.py \
    --match-name "Mon Match" \
    --video-1 /path/to/half1.mp4 \
    --video-2 /path/to/half2.mp4 \
    --checkpoint runs/best_model/best.pt
```

### 3. Ou utiliser le notebook Jupyter

```bash
jupyter notebook notebooks/upload_and_analyze_videos.ipynb
```

---

## Processus complet

```
📤 Upload vidéos (mi-temps 1 & 2)
        ↓
🔄 Extraire les features (5-15 min)
        ↓
🎯 Détecter les événements
        ↓
📊 Afficher les résultats
```

---

## Fichiers importants

| Fichier | Description |
|---------|-------------|
| `apps/api/upload_service.py` | Gestion des uploads |
| `apps/api/features_service.py` | Extraction de features ResNET |
| `apps/api/main.py` | Endpoints API |
| `apps/api/upload_example.py` | Script Python complet |
| `apps/api/schemas.py` | Modèles de données |
| `UPLOAD_VIDEO_GUIDE.md` | Guide détaillé |
| `notebooks/upload_and_analyze_videos.ipynb` | Notebook interactif |

---

## Endpoints principaux

```
POST   /upload/create                          # Créer un job
POST   /upload/{job_id}/video/{half}           # Upload vidéo (1 ou 2)
POST   /upload/{job_id}/finalize               # Finaliser upload
POST   /upload/{job_id}/extract-features       # Extraire features
POST   /upload/{job_id}/inference/run          # Lancer inférence
GET    /upload/{job_id}                        # État du job
```

---

## Formats supportés

✅ MP4, MKV, WebM, MOV, AVI

---

## Prérequis

- FFmpeg (`ffmpeg` command)
- Python 3.8+
- GPU optionnel (plus rapide pour les features)

---

## Problèmes courants

**FFmpeg non trouvé:**
```bash
# Windows (via Chocolatey)
choco install ffmpeg
```

**API non accessible:**
```bash
# Vérifier que l'API est démarrée
netstat -an | grep 8000
```

**Features extraction lente:**
```bash
# Utiliser GPU si disponible
--device cuda

# Réduire le nombre de frames
--fps 0.5
```

---

Pour plus de détails: voir [UPLOAD_VIDEO_GUIDE.md](UPLOAD_VIDEO_GUIDE.md)
