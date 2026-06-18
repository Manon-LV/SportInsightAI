# ✅ IMPLÉMENTATION COMPLÈTE - Import de Vidéos Personnalisées

Bienvenue! Cette documentation explique les modifications apportées à SportInsight AI pour permettre l'import et l'analyse de vos propres vidéos de matchs de football.

## 📚 Guide de navigation

### 🚀 Pour commencer rapidement (5 min)
→ Lire: [UPLOAD_QUICKSTART.md](UPLOAD_QUICKSTART.md)

### 📖 Pour comprendre la solution complète
→ Lire: [UPLOAD_VIDEO_GUIDE.md](UPLOAD_VIDEO_GUIDE.md)

### ⚙️ Pour installer les dépendances
→ Lire: [SETUP_VIDEO_UPLOAD.md](SETUP_VIDEO_UPLOAD.md)

### 🏗️ Pour comprendre l'architecture
→ Lire: [ARCHITECTURE_DIAGRAM.md](ARCHITECTURE_DIAGRAM.md)

### 📝 Pour voir les modifications faites
→ Lire: [MODIFICATIONS_SUMMARY.md](MODIFICATIONS_SUMMARY.md)

### 💻 Pour avoir les commandes essentielles
→ Utiliser: [QUICK_COMMANDS.sh](QUICK_COMMANDS.sh)

---

## 🎯 Cas d'usage principal

**Avant:** Vous deviez télécharger les vidéos depuis SoccerNet ou utiliser des vidéos de la base de données.

**Maintenant:** Vous pouvez uploader n'importe quelle vidéo de football (mi-temps 1 + mi-temps 2) et l'API analysera automatiquement:
- ✅ Extraction automatique des features (ResNET50)
- ✅ Détection des événements (buts, cartons, etc.)
- ✅ Affichage des résultats avec scores de confiance

---

## 🚀 Démarrage en 10 minutes

### Étape 1: Installer les dépendances (2 min)

```bash
# FFmpeg
choco install ffmpeg  # Windows
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux

# Python packages
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Étape 2: Démarrer l'API (1 min)

```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

### Étape 3: Uploader et analyser (7 min)

```bash
python apps/api/upload_example.py \
    --match-name "Mon Match" \
    --video-1 half1.mp4 \
    --video-2 half2.mp4 \
    --checkpoint runs/best.pt
```

Voilà! Les événements seront détectés et affichés.

---

## 📁 Fichiers créés/modifiés

### Services créés (Backend)
| Fichier | Fonction |
|---------|----------|
| `apps/api/upload_service.py` | Gestion des uploads |
| `apps/api/features_service.py` | Extraction ResNET |

### API modifiée
| Fichier | Changements |
|---------|------------|
| `apps/api/main.py` | +7 endpoints pour upload/features |
| `apps/api/schemas.py` | +3 schémas de données |

### Outils fournis
| Fichier | Utilité |
|---------|---------|
| `apps/api/upload_example.py` | Script Python complet |
| `apps/api/test_video_upload.py` | Tests unitaires |
| `notebooks/upload_and_analyze_videos.ipynb` | Tutorial interactif |

### Documentation complète
| Fichier | Contenu |
|---------|---------|
| `UPLOAD_QUICKSTART.md` | 5 min pour démarrer |
| `UPLOAD_VIDEO_GUIDE.md` | Guide complet (endpoints, exemples) |
| `SETUP_VIDEO_UPLOAD.md` | Installation et configuration |
| `ARCHITECTURE_DIAGRAM.md` | Vue d'ensemble de l'architecture |
| `MODIFICATIONS_SUMMARY.md` | Résumé des changements |
| `QUICK_COMMANDS.sh` | Toutes les commandes essentielles |

---

## 🔌 API Endpoints nouveaux

```
POST   /upload/create                        # Créer job
POST   /upload/{job_id}/video/{half}         # Upload vidéo
POST   /upload/{job_id}/finalize             # Finaliser
POST   /upload/{job_id}/extract-features     # Extraire features
GET    /upload/{job_id}                      # État du job
GET    /upload                               # Lister jobs
DELETE /upload/{job_id}                      # Supprimer job
```

---

## 📊 Workflow complet

```
1. Upload vidéo mi-temps 1
        ↓
2. Upload vidéo mi-temps 2
        ↓
3. Finaliser l'upload
        ↓
4. Extraire features ResNET (5-15 min) ⏱️
        ↓
5. Lancer inférence (détection d'événements)
        ↓
6. Afficher résultats (labels, scores, timestamps)
```

---

## 💡 Utilisation

### Via Python (recommandé)

```python
from apps.api.upload_example import SportInsightUploadClient

client = SportInsightUploadClient("http://localhost:8000")

result = client.upload_and_analyze(
    match_name="PSG vs Lyon",
    video_1_path="half1.mp4",
    video_2_path="half2.mp4",
    checkpoint="runs/best.pt"
)

print(f"Events found: {len(result['events'])}")
```

### Via Jupyter (interactif)

```bash
jupyter notebook notebooks/upload_and_analyze_videos.ipynb
```

### Via cURL (manuel)

```bash
# Voir UPLOAD_VIDEO_GUIDE.md pour détails complets
```

---

## ⚙️ Configuration

### Paramètres disponibles

| Paramètre | Valeur | Effet |
|-----------|--------|-------|
| `fps` | 0.5-5.0 | Nombre de frames à analyser (défaut: 2.0) |
| `device` | auto/cpu/cuda | GPU/CPU pour extraction (défaut: auto) |
| `score_threshold` | 0.0-1.0 | Confiance minimum (défaut: 0.30) |
| `nms_radius_sec` | 0-60 | Suppression d'événements proches |

### Optimisation

**Pour plus de rapidité:**
```bash
--fps 0.5 --device cuda
# ~5 min pour 45 min de vidéo avec GPU
```

**Pour plus de précision:**
```bash
--fps 5.0 --device cuda --score-threshold 0.50
# ~30 min pour 45 min de vidéo, meilleure détection
```

---

## 🐛 Problèmes courants

### ❌ "ffmpeg not found"
```bash
choco install ffmpeg  # Windows
brew install ffmpeg   # macOS
sudo apt install ffmpeg  # Linux
```

### ❌ "API not accessible"
```bash
# Vérifier que l'API est démarrée
curl http://localhost:8000/health

# Si non, démarrer:
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

### ❌ "Features extraction too slow"
```bash
# Utiliser GPU si disponible
--device cuda

# Réduire fps
--fps 0.5
```

---

## 📈 Performance

| Opération | Durée | Facteurs |
|-----------|-------|----------|
| Upload 100MB | 10-30s | Vitesse internet |
| Features 45min vidéo | 3-30min | GPU/CPU, fps |
| Inférence | 30s-2min | Nombre de frames |

---

## 🎓 Apprentissage

1. **Commencer:** UPLOAD_QUICKSTART.md
2. **Apprendre:** UPLOAD_VIDEO_GUIDE.md
3. **Explorer:** notebooks/upload_and_analyze_videos.ipynb
4. **Approfondir:** ARCHITECTURE_DIAGRAM.md

---

## ✅ Checklist d'installation

- [ ] FFmpeg installé (`ffmpeg --version`)
- [ ] PyTorch installé (`python -c "import torch; print(torch.__version__)"`)
- [ ] API démarre (`uvicorn apps.api.main:app --reload`)
- [ ] API répond (`curl http://localhost:8000/health`)
- [ ] Vidéos de test disponibles
- [ ] Checkpoint disponible (`curl http://localhost:8000/checkpoints`)

---

## 🚀 Prochaines étapes

1. **Installation:** Suivre SETUP_VIDEO_UPLOAD.md
2. **Test rapide:** Essayer UPLOAD_QUICKSTART.md
3. **Explorer:** Utiliser le notebook
4. **Produire:** Adapter pour vos vidéos

---

## 📞 Support

Pour des questions ou problèmes:
1. Vérifier la section "Problèmes courants"
2. Consulter les logs: `uvicorn apps.api.main:app --reload --log-level debug`
3. Vérifier les fichiers: `apps/api/storage/uploads/`
4. Utiliser le notebook pour tester étape par étape

---

## 📄 Licence

Voir le fichier LICENSE du projet principal.

---

**Status:** ✅ Prêt pour production  
**Version:** 0.3.0  
**Date:** 2024-06-17  
**Auteur:** GitHub Copilot  

