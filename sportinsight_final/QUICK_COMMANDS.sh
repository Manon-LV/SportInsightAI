#!/bin/bash

# =============================================================================
# 🚀 DÉMARRAGE RAPIDE - Import de vidéos personnalisées
# =============================================================================

# Cet script fournit toutes les commandes essentielles pour démarrer.
# À adapter selon votre configuration.

# =============================================================================
# 1. INSTALLATION
# =============================================================================

echo "📦 Installation des dépendances..."

# FFmpeg (requis)
echo "  Installing FFmpeg..."
# Windows (via Chocolatey)
# choco install ffmpeg

# macOS (via Homebrew)
# brew install ffmpeg

# Linux (Ubuntu/Debian)
# sudo apt-get update && sudo apt-get install -y ffmpeg

# PyTorch + TorchVision (pour extraction ResNET)
echo "  Installing PyTorch..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# FastAPI + uvicorn
pip install fastapi uvicorn pydantic

# Test
ffmpeg -version | head -n 1
python -c "import torch; print(f'PyTorch {torch.__version__}, GPU: {torch.cuda.is_available()}')"

# =============================================================================
# 2. DÉMARRER L'API
# =============================================================================

echo ""
echo "🚀 Démarrage de l'API..."
cd sportinsight_final

# Mode développement (avec rechargement automatique)
uvicorn apps.api.main:app --reload --host localhost --port 8000

# Mode production (optionnel)
# uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --workers 4

# =============================================================================
# 3. TEST DE SANTÉ
# =============================================================================

echo ""
echo "🏥 Test de l'API..."
curl http://localhost:8000/health | jq .

# =============================================================================
# 4. UPLOAD COMPLET (en parallèle)
# =============================================================================

echo ""
echo "🎬 Upload et analyse complet..."

# Via le script Python
python apps/api/upload_example.py \
    --match-name "Mon Match" \
    --video-1 /path/to/half1.mp4 \
    --video-2 /path/to/half2.mp4 \
    --checkpoint runs/best.pt \
    --fps 2.0 \
    --device auto

# =============================================================================
# 5. WORKFLOW MANUEL (cURL)
# =============================================================================

echo ""
echo "📡 Workflow manuel avec cURL..."

# 1. Créer job
JOB_ID=$(curl -s -X POST "http://localhost:8000/upload/create" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "match_name=Test Match" | jq -r '.job_id')

echo "Job ID: $JOB_ID"

# 2. Upload vidéos
echo "Uploading video 1..."
curl -X POST "http://localhost:8000/upload/$JOB_ID/video/1" \
    -F "file=@half1.mp4" > /dev/null

echo "Uploading video 2..."
curl -X POST "http://localhost:8000/upload/$JOB_ID/video/2" \
    -F "file=@half2.mp4" > /dev/null

# 3. Finaliser
echo "Finalizing..."
MATCH_DIR=$(curl -s -X POST "http://localhost:8000/upload/$JOB_ID/finalize" | jq -r '.match_dir')
echo "Match dir: $MATCH_DIR"

# 4. Extraire features
echo "Extracting features (this takes 5-15 minutes)..."
curl -X POST "http://localhost:8000/upload/$JOB_ID/extract-features" \
    -G -d "fps=2.0" -d "device=auto"

# 5. Inférence
echo "Running inference..."
curl -X POST "http://localhost:8000/inference/run" \
    -H "Content-Type: application/json" \
    -d "{
      \"match_dir\": \"$MATCH_DIR\",
      \"checkpoint\": \"runs/best.pt\",
      \"half\": \"both\"
    }" | jq .

# =============================================================================
# 6. UTILISER LE NOTEBOOK JUPYTER
# =============================================================================

echo ""
echo "📓 Notebook interactif..."

jupyter notebook notebooks/upload_and_analyze_videos.ipynb

# =============================================================================
# 7. TESTS
# =============================================================================

echo ""
echo "🧪 Exécuter les tests..."

python apps/api/test_video_upload.py --base-url http://localhost:8000

# =============================================================================
# 8. VOIR LES JOBS
# =============================================================================

echo ""
echo "📋 Lister tous les jobs..."

curl "http://localhost:8000/upload" | jq .

# =============================================================================
# 9. SUPPRIMER UN JOB
# =============================================================================

echo ""
echo "🗑️ Supprimer un job (optionnel)..."

# DELETE /upload/{job_id}
curl -X DELETE "http://localhost:8000/upload/$JOB_ID"

# =============================================================================
# COMMANDES UTILES
# =============================================================================

# Vérifier l'espace disque
du -sh apps/api/storage/

# Voir les logs en temps réel
tail -f /tmp/sportinsight-api.log

# Arrêter l'API (Ctrl+C)

# Lister les checkpoints
curl "http://localhost:8000/checkpoints" | jq '.[] | .name'

# Voir la vidéo complète
curl -X GET "http://localhost:8000/media/video" \
    -G \
    -d "match_dir=$MATCH_DIR" \
    -d "half=1" \
    -o match_half1.mp4

# =============================================================================
# TROUBLESHOOTING
# =============================================================================

# FFmpeg non trouvé?
which ffmpeg

# API ne démarre pas?
python -m fastapi --version
uvicorn --version

# Erreur GPU?
python -c "import torch; print(torch.cuda.get_device_name(0))"

# Vérifier les fichiers uploadés
ls -la apps/api/storage/uploads/

# =============================================================================
# DOCUMENTATION
# =============================================================================

# Pour plus d'informations:
# - UPLOAD_QUICKSTART.md       → 5 min pour commencer
# - UPLOAD_VIDEO_GUIDE.md      → Guide complet (endpoints, exemples)
# - SETUP_VIDEO_UPLOAD.md      → Installation détaillée
# - ARCHITECTURE_DIAGRAM.md    → Vue d'ensemble
# - MODIFICATIONS_SUMMARY.md   → Résumé des changements
