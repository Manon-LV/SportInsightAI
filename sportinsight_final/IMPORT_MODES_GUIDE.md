# 📤 Guide: Import de Matches - Vidéos vs Features

## 🎯 Deux modes d'importation

Le système SportInsight AI supporte désormais **deux modes d'importation** pour analyser vos matches:

### Mode 1️⃣: Upload de Vidéos (Extraction Automatique)
**Idéal pour:** Vous avez les vidéos du match et vous voulez que le système extraie les features

**Processus:**
1. Sélectionnez le mode **"📹 Uploader des vidéos"**
2. Entrez le nom du match
3. Uploadez les deux mi-temps (1.mp4 et 2.mp4)
4. Choisissez le modèle d'analyse
5. Cliquez sur **"Uploader et analyser"**

**Ce qui se passe:**
- ✅ Les vidéos sont uploadées sur le serveur
- ✅ Les frames sont extraites automatiquement (2 FPS par défaut)
- ✅ ResNET50 extrait les features (2048D) de chaque frame
- ✅ Les fichiers `.npy` sont créés:
  - `1_ResNET_TF2_PCA512.npy` (mi-temps 1)
  - `2_ResNET_TF2_PCA512.npy` (mi-temps 2)
- ✅ L'analyse est lancée automatiquement

**Durée estimée:** 30 minutes à 2 heures (selon la vidéo et votre CPU)

**Avantages:**
- 📹 Contrôle complet des vidéos
- 🔄 Extraction automatique
- ⚙️ Pas de configuration nécessaire

---

### Mode 2️⃣: Import de Features Pré-extraites
**Idéal pour:** Vous avez déjà les fichiers `.npy` d'un modèle ResNET50 et vous voulez analyser directement

**Processus:**
1. Sélectionnez le mode **"📊 Importer des features pré-extraites"**
2. Entrez le nom du match
3. Uploadez les deux fichiers `.npy`:
   - `1_ResNET_TF2_PCA512.npy`
   - `2_ResNET_TF2_PCA512.npy`
4. Choisissez le modèle d'analyse
5. Cliquez sur **"Importer et analyser"**

**Ce qui se passe:**
- ✅ Les fichiers `.npy` sont uploadés directement
- ✅ Pas d'extraction vidéo nécessaire
- ✅ L'analyse est lancée immédiatement

**Durée estimée:** < 1 minute (simple copie de fichiers)

**Avantages:**
- 🚀 Très rapide (pas d'extraction)
- 📊 Réutilisabilité (si vous avez déjà les features)
- ⏱️ Analyse immédiate

---

## 📋 Format des fichiers .npy

Les fichiers de features doivent respecter ce format:

```
Fichier: 1_ResNET_TF2_PCA512.npy
Type: NumPy array (ndarray)
Shape: (num_frames, 2048)
dtype: float32 ou float64
```

**Exemple:**
- Pour une vidéo de 10 minutes à 25 FPS avec extraction à 2 FPS:
- num_frames = (10 * 60 * 25) / 2 = 7,500 frames
- Taille du fichier ≈ 7,500 × 2,048 × 8 bytes ≈ **122 MB**

---

## 🔄 Endpoints API

### Mode Vidéo
```bash
# 1. Créer un job
POST /upload/create
Body: { "match_name": "PSG vs Lyon" }
Response: { "job_id": "uuid" }

# 2. Upload vidéo mi-temps 1
POST /upload/{job_id}/video/1
Body: FormData with video file
Response: { "path": "...", "size": ... }

# 3. Upload vidéo mi-temps 2
POST /upload/{job_id}/video/2
Body: FormData with video file

# 4. Finaliser l'upload
POST /upload/{job_id}/finalize
Response: { "match_dir": "..." }

# 5. Extraire les features
POST /upload/{job_id}/extract-features?fps=2.0&device=auto
Response: { "halves": { "1": {...}, "2": {...} } }

# 6. Vérifier l'état
GET /upload/{job_id}
Response: UploadStatus
```

### Mode Features Directs
```bash
# 1. Créer un job (même que vidéo)
POST /upload/create
Body: { "match_name": "PSG vs Lyon" }
Response: { "job_id": "uuid" }

# 2. Upload features mi-temps 1
POST /upload/{job_id}/upload-features
Body: FormData
  - half: 1
  - file: 1_ResNET_TF2_PCA512.npy

# 3. Upload features mi-temps 2
POST /upload/{job_id}/upload-features
Body: FormData
  - half: 2
  - file: 2_ResNET_TF2_PCA512.npy

# 4. Vérifier l'état
GET /upload/{job_id}
Response: UploadStatus (features_status: "done")
```

---

## 💡 Cas d'usage

| Situation | Mode | Raison |
|-----------|------|--------|
| J'ai des vidéos MP4 | Vidéos | ✅ Le système extrait les features |
| J'ai déjà les .npy | Features | ✅ Analyse immédiate |
| Je veux tester rapidement | Features | ✅ Plus rapide |
| Je ne connais pas le format .npy | Vidéos | ✅ Plus simple |
| Je dois traiter 100 matches | Vidéos | ✅ Stockage centralisé |
| Je veux réutiliser des features | Features | ✅ Une fois extraits, ils servent plusieurs fois |

---

## ⚙️ Configuration

### Extraction Vidéo (Mode 1)
Paramètres disponibles lors de l'extraction:
- **fps**: Frames par seconde à extraire (défaut: 2.0)
  - ↓ FPS = moins de frames = plus rapide + moins détails
  - ↑ FPS = plus de frames = plus lent + plus détails
- **device**: CPU ou GPU (défaut: auto)
  - `cpu` = CPU uniquement
  - `cuda` = GPU NVIDIA (si disponible)
  - `auto` = détection automatique

### Importer Features (Mode 2)
Aucune configuration nécessaire - import direct du fichier `.npy`

---

## 🐛 Troubleshooting

### "Fichier .npy non reconnu"
- ✅ Vérifiez que le fichier se termine par `.npy`
- ✅ Vérifiez que le shape est (num_frames, 2048)
- ✅ Vérifiez que c'est un NumPy array valide

### "Extraction vidéo trop lente"
- ✅ Utilisez `fps=1.0` au lieu de `2.0` (moins de frames)
- ✅ Utilisez `device=cpu` explicitement
- ✅ Comprimez les vidéos avant l'upload

### "Match directory not set"
- ✅ Assurez-vous d'avoir créé un job avec `/upload/create` d'abord
- ✅ Vérifiez que l'ID du job est correct

---

## 📚 Ressources

- [Guide complet d'upload](UPLOAD_GUIDE.md)
- [Format des features ResNET](FEATURES_FORMAT.md)
- [FAQ Extraction vidéo](FAQ_VIDEO_EXTRACTION.md)
