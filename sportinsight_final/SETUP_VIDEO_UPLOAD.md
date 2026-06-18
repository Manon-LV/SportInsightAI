# Configuration pour l'import et l'analyse de vidéos personnalisées

## Installation

### 1. Installer FFmpeg

**Windows (Chocolatey):**
```powershell
choco install ffmpeg
```

**Windows (Manuelle):**
- Télécharger depuis https://ffmpeg.org/download.html
- Ajouter au PATH

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

### 2. Installer les dépendances Python

```bash
# Installation basique (CPU)
pip install fastapi uvicorn pydantic pydantic-settings

# Avec support GPU (recommandé)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Alternative (AMD GPU)
pip install torch torchvision rocm --index-url https://download.pytorch.org/whl/rocm5.7
```

### 3. Vérifier l'installation

```bash
# Vérifier FFmpeg
ffmpeg -version

# Vérifier PyTorch
python -c "import torch; print(f'PyTorch {torch.__version__}'); print(f'GPU: {torch.cuda.is_available()}')"

# Vérifier torchvision
python -c "import torchvision; print(f'torchvision {torchvision.__version__}')"
```

## Variables d'environnement (optionnel)

```bash
# Pour forcer le CPU (par défaut auto-détecte)
export CUDA_VISIBLE_DEVICES=-1

# Ou via Python
import os
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'
```

## Structure des fichiers générés

```
apps/api/storage/uploads/
├── upload_a1b2c3d4e5f6/           # Job ID
│   └── Mon Match/
│       ├── 1.mp4                  # Vidéo mi-temps 1 (uploadée)
│       ├── 2.mp4                  # Vidéo mi-temps 2 (uploadée)
│       ├── 1_ResNET_TF2_PCA512.npy    # Features mi-temps 1 (extrait)
│       └── 2_ResNET_TF2_PCA512.npy    # Features mi-temps 2 (extrait)
│
├── upload_xyz123/
│   └── ...
```

## Configuration de l'API

### Port personnalisé

```bash
uvicorn apps.api.main:app --port 9000
```

### Mode production

```bash
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Avec Gunicorn

```bash
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker apps.api.main:app
```

## Limits et optimisations

### Limites recommandées

| Paramètre | Limite | Raison |
|-----------|--------|--------|
| Taille vidéo | < 1 GB | Performance upload |
| Durée vidéo | < 90 min | Temps extraction |
| FPS extraction | 0.5 - 5.0 | Balance qualité/vitesse |
| Batch d'uploads | 1-2 simultanés | Limitation mémoire |

### Optimisations

**Pour plus de vitesse:**
```python
# features_service.py - Réduire fps
fps = 1.0  # Au lieu de 2.0

# Utiliser GPU
device = "cuda"

# Réduire résolution des vidéos avant upload
ffmpeg -i input.mp4 -vf scale=720:-1 output.mp4
```

**Pour plus de qualité:**
```python
# Augmenter fps
fps = 5.0

# Uploader en haute résolution
# (sera re-scalée à 224x224 de toute façon)
```

## Troubleshooting

### FFmpeg non trouvé

```bash
# Vérifier le PATH
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows

# Si absent, ajouter au PATH manuellement
# Puis redémarrer le terminal
```

### Erreur CUDA

```bash
# Vérifier GPU disponible
python -c "import torch; print(torch.cuda.is_available())"

# Si False, forcer CPU
--device cpu
```

### Erreur de mémoire

```bash
# Réduire fps
--fps 0.5

# Traiter une seule mi-temps à la fois
# Augmenter la RAM disponible
```

### Erreur PyTorch

```bash
# Réinstaller PyTorch
pip uninstall torch torchvision -y
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Performance indicative

### Hardware requis

| Composant | Minimum | Recommandé |
|-----------|---------|-----------|
| CPU | 4 cores | 8+ cores |
| RAM | 8 GB | 16 GB |
| Stockage | 50 GB | 200 GB |
| GPU | - | NVIDIA GTX 1080 (8GB) |

### Temps d'exécution (45 min vidéo)

| Configuration | Extraction | Total |
|---------------|-----------|-------|
| CPU (4c, 8GB) | 25-30 min | 35-40 min |
| CPU (8c, 16GB) | 12-15 min | 22-25 min |
| GPU (GTX 1080) | 3-4 min | 13-16 min |
| GPU (RTX 3090) | 1-2 min | 11-13 min |

## Support

- Vérifier les logs: `uvicorn apps.api.main:app --reload --log-level debug`
- Vérifier les fichiers: `apps/api/storage/uploads/`
- Utiliser le notebook: `notebooks/upload_and_analyze_videos.ipynb`
