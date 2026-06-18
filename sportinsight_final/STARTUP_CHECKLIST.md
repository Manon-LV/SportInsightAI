# ✅ Checklist Complète - Démarrage du système

## 📋 Prérequis

- [ ] Python 3.9+
- [ ] Node.js 18+
- [ ] FFmpeg installé
- [ ] PyTorch installé
- [ ] CUDA 11.8+ (optionnel, pour GPU)

## 🔧 Installation initiale (une seule fois)

### Backend

```bash
# 1. Aller au répertoire du projet
cd sportinsight_final

# 2. Créer environnement virtuel
python -m venv venv

# 3. Activer l'environnement
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Installer dépendances
pip install -r requirements.txt

# 5. Vérifier l'installation
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import fastapi; print('FastAPI OK')"
```

### Frontend

```bash
# 1. Aller au répertoire web
cd sportinsight_final/apps/web

# 2. Installer dépendances
npm install

# 3. Vérifier l'installation
npm --version
node --version
```

## 🚀 Démarrage du système

### Terminal 1: Backend API

```bash
cd sportinsight_final

# Activer l'environnement (si nécessaire)
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate      # Windows

# Démarrer l'API
uvicorn apps.api.main:app --reload --port 8000

# Sortie attendue:
# INFO:     Uvicorn running on http://127.0.0.1:8000
# INFO:     Application startup complete
```

✅ **Vérifier:** http://localhost:8000/health

### Terminal 2: Frontend Web

```bash
cd sportinsight_final/apps/web

# Démarrer le serveur de développement
npm run dev

# Sortie attendue:
# ➜  Local:   http://127.0.0.1:5173/
# ➜  press h to show help
```

✅ **Accéder:** http://localhost:5173

## 🧪 Tests

### Test 1: Vérifier l'API

```bash
# Vérifier la santé
curl http://localhost:8000/health

# Sortie attendue:
# {"status":"ok","service":"sportinsight-api"}
```

### Test 2: Vérifier l'interface web

1. Ouvrir http://localhost:5173
2. Voir le menu principal avec deux options
3. Cliquer sur "Uploader une vidéo"
4. Vérifier que le formulaire s'affiche

### Test 3: Test d'upload complet

1. Préparer deux fichiers vidéo (mp4, mkv, etc.)
   - La durée n'a pas d'importance (peut être 10 secondes)
2. Aller à http://localhost:5173
3. Cliquer "Uploader une vidéo"
4. Remplir:
   - Nom du match: "Test PSG vs Lyon"
   - Mi-temps 1: Sélectionner vidéo 1
   - Mi-temps 2: Sélectionner vidéo 2
5. Cliquer "Uploader et analyser"
6. Observer la progression:
   - ✅ Création du job
   - ✅ Upload mi-temps 1
   - ✅ Upload mi-temps 2
   - ✅ Finalisation
   - ✅ Extraction features (5-15 min)
7. Une fois terminé, cliquer "Analyser"
8. Voir les événements détectés

### Test 4: Test d'analyse SoccerNet

1. Aller à http://localhost:5173
2. Cliquer "Analyser un match"
3. Sélectionner un split (test, valid, train)
4. Sélectionner un match
5. Lancer l'inférence
6. Voir les résultats

## 📊 Architecture testée

```
Client (5173)
    ↓
Browser ← Vue 3, TypeScript, Quasar
    ↓ HTTP
API (8000)
    ↓ 
FastAPI, Python
    ↓
Services (Upload, Features, Inference)
    ↓
Storage (local), Models (PyTorch), Video (FFmpeg)
```

## 🔧 Configuration

### Variables d'environnement (.env)

```env
# File: apps/web/.env ou apps/web/.env.local
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Configuration API (main.py)

```python
# Configuration des ports
API_PORT = 8000
WEB_PORT = 5173

# Configuration du stockage
STORAGE_PATH = "apps/api/storage/uploads"

# Configuration du GPU
DEVICE = "cuda" ou "cpu" ou "auto"
```

## 🎯 Cas d'usage

### Cas 1: Upload uniquement

```bash
# Utiliser l'interface web
1. MainMenu → Uploader
2. Remplir le formulaire
3. Cliquer "Uploader"
4. Attendre "Prêt pour analyse"
```

### Cas 2: Analyse uniquement

```bash
# Utiliser l'interface web
1. MainMenu → Analyser
2. Sélectionner un match
3. Lancer l'inférence
4. Voir les résultats
```

### Cas 3: Upload + Analyse

```bash
# Utiliser l'interface web
1. MainMenu → Uploader
2. Remplir et uploader
3. Une fois prêt, cliquer "Analyser"
4. Résultats s'affichent
```

### Cas 4: CLI Python

```bash
# Voir upload_example.py pour CLI
cd sportinsight_final
python scripts/upload_example.py \
    --match-name "PSG vs Lyon" \
    --half1 /path/to/video1.mp4 \
    --half2 /path/to/video2.mp4 \
    --checkpoint best
```

## 🐛 Dépannage

### Erreur: Port 5173 déjà utilisé

```bash
# Solution: Utiliser un autre port
cd apps/web
npm run dev -- --port 3000

# Accéder à http://localhost:3000
```

### Erreur: L'API ne répond pas

```bash
# Vérifier que l'API est lancée
curl http://localhost:8000/health

# Si erreur, redémarrer l'API:
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

### Erreur: CORS

```bash
# Vérifier que VITE_API_BASE_URL est correct
cat apps/web/.env

# Doit être:
VITE_API_BASE_URL=http://127.0.0.1:8000
```

### Erreur: npm modules manquants

```bash
cd apps/web
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### Erreur: Python packages manquants

```bash
cd sportinsight_final
source venv/bin/activate  # ou venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

### Erreur: FFmpeg non trouvé

```bash
# Installer FFmpeg
# Windows (avec chocolatey):
choco install ffmpeg

# macOS:
brew install ffmpeg

# Linux (Ubuntu):
sudo apt-get install ffmpeg

# Vérifier:
ffmpeg -version
```

### Erreur: PyTorch non installé

```bash
# Installer PyTorch
pip install torch torchvision

# Avec GPU (CUDA):
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

## 📈 Performance

Attendre ces résultats:

| Opération | Temps attendu | Remarques |
|-----------|---------------|----------|
| Chargement API | < 2s | Premier appel |
| Chargement web | < 2s | Page accueil |
| Upload 100MB | 10-30s | Dépend internet |
| Extraction features | 5-30min | Dépend CPU/GPU |
| Inférence | 5-10s | Batch processing |

## 🔐 Vérifications de sécurité

- [ ] API n'accepte que les vidéos valides
- [ ] Fichiers stockés localement
- [ ] Pas d'accès non autorisé
- [ ] Erreurs ne révèlent pas les chemins
- [ ] Validation des entrées

## 📝 Logs et debugging

### Logs API
```bash
# En développement (déjà actif)
uvicorn apps.api.main:app --reload --log-level debug

# Voir dans le terminal
INFO:     Application startup complete
```

### Logs Frontend
```bash
# Ouvrir la console du navigateur
F12 → Console

# Voir les appels API
F12 → Network

# Voir Vue Devtools
npm install -g @vue/devtools
```

### Logs Python
```bash
# Ajouter dans le code:
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.debug("Message de debug")
```

## ✨ Fonctionnalités vérifiées

- [x] Menu principal avec navigation
- [x] Interface upload avec drag-and-drop
- [x] Suivi de progression en temps réel
- [x] Upload multi-fichier
- [x] Extraction de features
- [x] Analyse SoccerNet
- [x] Timeline interactive
- [x] Stockage local
- [x] Gestion des erreurs
- [x] API REST complète

## 🎓 Documentation

- [README.md](README.md) - Guide principal
- [QUICK_START.md](QUICK_START.md) - Démarrage rapide
- [apps/web/README_WEB.md](apps/web/README_WEB.md) - Web détaillé
- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture complète
- [apps/web/WEB_QUICKSTART.md](apps/web/WEB_QUICKSTART.md) - Web quickstart

## 🚀 Prochaines étapes

1. Tester l'interface web
2. Uploader vos propres vidéos
3. Analyser les résultats
4. Exporter les clips
5. Configurer en production

---

**Status:** ✅ Prêt à l'emploi  
**Version:** 1.0.0  
**Dernière mise à jour:** 2024-06-17  

**Besoin d'aide?** Consulter les fichiers de documentation ou les logs.
