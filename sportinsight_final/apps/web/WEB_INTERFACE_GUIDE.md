# 🌐 Interface Web - Upload de Vidéos

## 📋 Vue d'ensemble

La nouvelle interface web de SportInsight AI propose:
- ✅ **Menu principal** - Navigation entre "Analyser" et "Uploader"
- ✅ **Uploader vidéos** - Interface drag-and-drop pour les 2 mi-temps
- ✅ **Suivi en temps réel** - Progression de l'upload et extraction
- ✅ **Intégration API** - Communication directe avec le backend

---

## 🚀 Démarrage rapide

### 1. Démarrer l'API backend
```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

### 2. Démarrer l'interface web
```bash
cd sportinsight_final/apps/web
npm install  # si besoin
npm run dev
```

### 3. Accéder à l'interface
```
http://localhost:5173
```

---

## 📱 Interface utilisateur

### Menu principal
```
┌─────────────────────────────────────────┐
│         SportInsight AI                 │
│                                         │
│  ┌──────────────┐  ┌──────────────┐    │
│  │   Analyser   │  │   Uploader   │    │
│  │              │  │              │    │
│  │   Matches    │  │   Vidéos     │    │
│  │   SoccerNet  │  │ personnelles  │    │
│  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────┘
```

### Interface d'upload
```
┌────────────────────────────────────────────┐
│        📤 Upload de Vidéo de Match         │
├────────────────────────────────────────────┤
│ 1️⃣ Informations du match                  │
│    [Nom du match           ]               │
│                                            │
│ 2️⃣ Upload des vidéos                      │
│    Mi-temps 1 [Drag & Drop]               │
│    Mi-temps 2 [Drag & Drop]               │
│                                            │
│ 3️⃣ Modèle d'analyse                       │
│    [Checkpoint            ▼]               │
│                                            │
│          [Annuler] [Uploader et analyser]  │
└────────────────────────────────────────────┘
```

---

## 🎯 Workflow complet

### Étape 1: Sélectionner "Uploader une vidéo"
- Cliquez sur la carte "Uploader une vidéo"
- Vous êtes redirigé vers l'interface d'upload

### Étape 2: Informations du match
- Entrez le nom du match (ex: "PSG vs Lyon")
- Ce nom sera utilisé comme dossier de destination

### Étape 3: Upload des vidéos
Deux options:

**Option A: Glisser-déposer**
- Glissez la vidéo mi-temps 1 sur la zone pointillée
- Glissez la vidéo mi-temps 2 sur la zone pointillée

**Option B: Cliquer pour sélectionner**
- Cliquez sur la zone pointillée
- Sélectionnez le fichier depuis votre ordinateur

### Étape 4: Sélectionner le modèle
- Choisissez le checkpoint d'analyse
- Le modèle par défaut sera sélectionné si disponible

### Étape 5: Uploader et analyser
- Cliquez sur "Uploader et analyser"
- Le processus se déroule en direct:
  1. Création du job
  2. Upload mi-temps 1
  3. Upload mi-temps 2
  4. Finalisation
  5. Extraction des features ResNET (5-15 min)
  6. Prêt pour l'analyse

### Étape 6: Analyse des résultats
- Une fois les features extraites
- Cliquez sur "Analyser maintenant"
- Vous êtes redirigé vers l'analyseur avec les données du match uploadé

---

## 🎨 Fonctionnalités UI

### Zones d'upload intelligentes
- **Drag & Drop**: Glissez n'importe quel fichier vidéo
- **Visuelle**: La zone change de couleur lors du survol
- **Validation**: Affiche le nom et la taille du fichier

### Suivi de progression
- **Étapes nominées**: Voir chaque étape du processus
- **Barre de progression**: Suivi visuel de l'avancement
- **Messages détaillés**: Informations sur l'étape actuelle

### Gestion des états
- **Avant upload**: Interface normale
- **Pendant upload**: Mode chargement avec progression
- **Après upload**: Affichage du job ID et options d'action

### Formats supportés
- ✅ MP4
- ✅ MKV
- ✅ WebM
- ✅ MOV
- ✅ AVI

---

## 🔧 Configuration

### Variables d'environnement

Créer un fichier `.env` à la racine du projet web:

```env
VITE_API_BASE_URL=http://localhost:8000
```

### Package.json scripts

```bash
# Développement avec hot-reload
npm run dev

# Build production
npm run build

# Aperçu du build
npm run preview
```

---

## 📊 Structure des composants

```
App.vue (Point d'entrée)
├── MainMenu.vue (Navigation principale)
│   ├── AnalystRoom.vue (Analyse existante)
│   └── VideoUploader.vue (Upload vidéos)
│       ├── Formulaire d'upload
│       ├── Zones drag-and-drop
│       ├── Barre de progression
│       └── Affichage du résultat
└── services/
    └── api.ts (Appels API)
```

---

## 🔌 Intégration API

### Endpoints utilisés

```typescript
// Créer un job d'upload
POST /upload/create

// Upload vidéo
POST /upload/{job_id}/video/{half}

// Finaliser l'upload
POST /upload/{job_id}/finalize

// Extraire features
POST /upload/{job_id}/extract-features

// Récupérer le statut
GET /upload/{job_id}

// Lister les checkpoints
GET /checkpoints

// Lancer l'inférence
POST /inference/run
```

### Exemple d'appel

```typescript
import { 
  createUploadJob, 
  uploadVideo, 
  finalizeUpload,
  extractFeatures 
} from './services/api'

// Créer job
const job = await createUploadJob('PSG vs Lyon')

// Upload vidéos
await uploadVideo(job.job_id, 1, file1)
await uploadVideo(job.job_id, 2, file2)

// Finaliser
await finalizeUpload(job.job_id)

// Extraire features
await extractFeatures(job.job_id)
```

---

## 🎓 Utilisation pratique

### Cas 1: Upload simple
1. Cliquer sur "Uploader une vidéo"
2. Remplir les informations
3. Glisser-déposer les vidéos
4. Cliquer sur "Uploader"
5. Attendre la fin (affichée dans la barre)
6. Cliquer sur "Analyser maintenant"

### Cas 2: Analyse d'un match SoccerNet
1. Cliquer sur "Analyser un match"
2. Sélectionner le match dans la liste
3. Lancer l'analyse
4. Voir les résultats

### Cas 3: Monitorage du job d'upload
1. Cliquer sur "Rafraîchir" pour actualiser le statut
2. Le job ID est affiché et copiable
3. Voir le répertoire d'extraction

---

## 🐛 Dépannage

### L'API n'est pas accessible
```
❌ Error: Failed to fetch from http://localhost:8000
```
**Solution:**
- Vérifier que l'API est démarrée: `uvicorn apps.api.main:app --reload`
- Vérifier le port: 8000
- Vérifier CORS dans les en-têtes

### Fichier trop volumineux
```
❌ Error: File is too large
```
**Solution:**
- Réduire la taille de la vidéo avec FFmpeg
- Uploader les fichiers séparément
- Utiliser la ligne de commande au lieu du web

### Les checkpoints ne s'affichent pas
```
❌ Aucun checkpoint disponible
```
**Solution:**
- Vérifier que les fichiers .pt existent: `runs/*/best.pt`
- Vérifier que l'API peut y accéder
- Consulter les logs de l'API

### L'extraction de features est lente
```
⏱️ Prend plus de 20 minutes
```
**Solution:**
- Utiliser un GPU: Configurez CUDA
- Réduire les frames par seconde
- Utiliser la ligne de commande pour plus de contrôle

---

## 📈 Performance

| Opération | Durée | Facteur |
|-----------|-------|--------|
| Upload 100MB | 10-30s | Internet |
| Extraction features | 3-30min | GPU/CPU |
| Interface | < 100ms | Réactif |

---

## 🔐 Sécurité

- ✅ Stockage local uniquement
- ✅ HTTPS recommandé en production
- ✅ Validation côté client et serveur
- ✅ Gestion des erreurs sans exposition

---

## 🚀 Déploiement

### Développement local
```bash
npm run dev
```

### Build production
```bash
npm run build
# Fichiers dans dist/
```

### Docker
```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

---

## 📝 Notes

- Les vidéos sont stockées dans `apps/api/storage/uploads/`
- Les features extraites sont au format .npy
- Les résultats sont JSON
- Les fichiers de log sont disponibles via l'API

---

## 🔮 Améliorations futures

- [ ] Upload multiple (batch)
- [ ] Historique des uploads
- [ ] Paramètres d'extraction configurables dans l'UI
- [ ] Graphiques en temps réel
- [ ] Export des résultats
- [ ] Partage de résultats

---

**Status:** ✅ Prêt pour utilisation  
**Version:** 1.0.0  
**Dernière mise à jour:** 2024-06-17  

