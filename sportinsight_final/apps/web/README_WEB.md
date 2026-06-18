# 🌐 Interface Web - SportInsight AI

Interface web interactive pour uploader et analyser des vidéos de matchs de football.

## ✨ Fonctionnalités

- 🎬 **Upload de vidéos** - Glisser-déposer pour mi-temps 1 et 2
- 📊 **Analyse en temps réel** - Suivi de la progression avec barre visuelle
- 🎯 **Détection d'événements** - Événements détectés automatiquement
- 📈 **Visualisation** - Timeline interactive des événements
- 🔄 **Workflow complet** - Upload → Features → Analyse

## 🚀 Démarrage rapide

### 1. Démarrer le backend
```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

### 2. Démarrer le frontend
```bash
cd sportinsight_final/apps/web
npm install  # première fois seulement
npm run dev
```

### 3. Accéder à l'interface
```
http://localhost:5173
```

## 📁 Structure du projet

```
apps/web/
├── src/
│   ├── components/
│   │   ├── VideoUploader.vue       # Interface d'upload
│   │   ├── Timeline.vue             # Timeline des événements
│   │   ├── EventList.vue            # Liste des événements
│   │   └── ...
│   ├── pages/
│   │   ├── MainMenu.vue             # Menu principal
│   │   ├── AnalystRoom.vue          # Interface d'analyse
│   │   └── ...
│   ├── services/
│   │   └── api.ts                   # Appels API
│   ├── types/
│   │   └── predictions.ts           # Types TypeScript
│   ├── App.vue                      # Point d'entrée
│   └── main.ts                      # Configuration
├── .env.example                     # Variables d'environnement
├── package.json                     # Dépendances
├── tsconfig.json                    # Config TypeScript
├── vite.config.ts                   # Config Vite
└── README.md                        # Ce fichier
```

## 🎨 Pages principales

### MainMenu.vue
Page d'accueil avec deux options:
- **Analyser un match** - Accès aux matchs SoccerNet ou uploadés
- **Uploader une vidéo** - Interface pour uploader vos vidéos

### AnalystRoom.vue
Interface d'analyse complète:
- Sélection du match
- Sélection du checkpoint
- Lancement de l'inférence
- Timeline interactive
- Liste des événements

### VideoUploader.vue
Interface d'upload:
- Saisie du nom du match
- Zones drag-and-drop
- Sélection du checkpoint
- Barre de progression
- Suivi du job

## 🔌 API Endpoints

| Endpoint | Méthode | Description |
|----------|---------|-------------|
| `/upload/create` | POST | Créer un job d'upload |
| `/upload/{job_id}/video/{half}` | POST | Uploader une vidéo |
| `/upload/{job_id}/finalize` | POST | Finaliser l'upload |
| `/upload/{job_id}/extract-features` | POST | Extraire les features |
| `/upload/{job_id}` | GET | Récupérer le statut |
| `/inference/run` | POST | Lancer l'inférence |
| `/checkpoints` | GET | Lister les checkpoints |
| `/splits/{name}/matches` | GET | Lister les matches |

## 🛠️ Configuration

### Variables d'environnement

Créer un fichier `.env` ou `.env.local`:

```env
# URL de l'API backend
VITE_API_BASE_URL=http://localhost:8000

# Thème (optionnel)
# VITE_QUASAR_THEME=light
```

Voir `.env.example` pour les options disponibles.

## 📦 Installation

### Prérequis
- Node.js 18+
- npm ou yarn
- Backend API en cours d'exécution

### Installation des dépendances
```bash
npm install
```

### Développement
```bash
npm run dev
```

### Build production
```bash
npm run build
```

### Aperçu du build
```bash
npm run preview
```

## 🎯 Utilisation

### Workflow upload + analyse

1. **Cliquer sur "Uploader une vidéo"** depuis le menu
2. **Entrer le nom du match**
3. **Glisser-déposer les vidéos** (mi-temps 1 et 2)
4. **Sélectionner le modèle** d'analyse
5. **Cliquer "Uploader et analyser"**
6. **Suivre la progression** sur la barre visuelle
7. **Voir les résultats** une fois les features extraites
8. **Cliquer "Analyser"** pour voir les événements détectés

### Workflow analyse SoccerNet

1. **Cliquer sur "Analyser un match"** depuis le menu
2. **Sélectionner le split** (train/test/valid)
3. **Choisir un match** dans la liste
4. **Sélectionner le checkpoint**
5. **Lancer l'inférence**
6. **Voir les résultats** en temps réel

## 🎨 Styling

- Framework: **Quasar** (composants Material Design)
- Styling: **SCSS** avec variables Quasar
- Thème: Cyan/Orange par défaut
- Mode sombre: Supporté (configurable)

## 🧪 Testing

```bash
# Lint
npm run lint

# Build
npm run build

# Preview
npm run preview
```

## 🚀 Déploiement

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
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx configuration
```nginx
server {
    listen 80;
    server_name _;

    location / {
        root /usr/share/nginx/html;
        try_files $uri /index.html;
    }

    location /api {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🐛 Dépannage

### Port 5173 déjà utilisé
```bash
npm run dev -- --port 3000
```

### L'API ne répond pas
- Vérifier que le backend est démarré sur le port 8000
- Vérifier CORS dans les en-têtes API
- Vérifier la variable `VITE_API_BASE_URL`

### Fichiers non trouvés (404)
```bash
npm install
npm run dev
```

### Build échoue
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

## 📚 Documentation complète

- [WEB_QUICKSTART.md](WEB_QUICKSTART.md) - Démarrage rapide
- [WEB_INTERFACE_GUIDE.md](WEB_INTERFACE_GUIDE.md) - Guide détaillé
- [../README.md](../README.md) - Documentation générale

## 🔗 Composants principaux

### VideoUploader.vue
- Zones drag-and-drop
- Upload multi-fichier
- Barre de progression
- Gestion des erreurs

### AnalystRoom.vue
- Sélection des données
- Lancement de l'inférence
- Affichage des résultats
- Timeline interactive

### Timeline.vue
- Visualisation temporelle
- Événements codés par couleur
- Navigation interactive
- Export d'images

### EventList.vue
- Liste filtrable
- Tri par temps/confiance
- Détails complets
- Lien vers vidéo

## 📊 Type Definitions

```typescript
interface UploadStatus {
  job_id: string
  status: string // 'uploading' | 'processing' | 'done' | 'error'
  match_name: string
  half_1_path?: string
  half_2_path?: string
  features_status: string
  match_dir?: string
  error?: string
}

interface EventPrediction {
  event_type: string
  timestamp: number
  confidence: number
  half: number
  [key: string]: any
}

interface InferenceRequest {
  match_dir: string
  checkpoint: string
  [key: string]: any
}

interface InferenceResponse {
  match_dir: string
  half_1: EventPrediction[]
  half_2: EventPrediction[]
  [key: string]: any
}
```

## 🔄 Lifecycle des données

```
Upload Vidéo
    ↓
Extraction Frames (FFmpeg)
    ↓
Features ResNET (GPU)
    ↓
Sauvegarde .npy
    ↓
Lancement Inférence
    ↓
Détection d'Événements
    ↓
Affichage Résultats
```

## 🎓 Exemples d'utilisation

### JavaScript/TypeScript
```typescript
import { 
  createUploadJob, 
  uploadVideo,
  extractFeatures,
  runInference 
} from './services/api'

// Créer job
const job = await createUploadJob('PSG vs Lyon')

// Upload
await uploadVideo(job.job_id, 1, file1)
await uploadVideo(job.job_id, 2, file2)

// Features
await extractFeatures(job.job_id)

// Inférence
const results = await runInference({
  match_dir: job.match_dir,
  checkpoint: 'best'
})
```

### Vue 3 Component
```vue
<template>
  <VideoUploader @analyze="handleAnalyze" />
</template>

<script setup>
import VideoUploader from './components/VideoUploader.vue'

function handleAnalyze(data) {
  console.log('Match prêt:', data.match_dir)
}
</script>
```

## 🔐 Sécurité

- ✅ Validation côté client et serveur
- ✅ Stockage local uniquement
- ✅ Gestion des erreurs sans exposition
- ✅ Timeouts configurés
- ✅ HTTPS recommandé en production

## 📈 Performance

- **Temps de chargement**: < 2s
- **Interaction**: < 100ms
- **Upload**: Dépend de la vitesse internet
- **Features**: 5-30 min (GPU/CPU)

## 🤝 Contributing

1. Créer une branche: `git checkout -b feature/ma-feature`
2. Faire les modifications
3. Tester: `npm run build`
4. Commit: `git commit -am 'Ajouter ma-feature'`
5. Push: `git push origin feature/ma-feature`

## 📝 License

MIT - Voir LICENSE pour plus de détails

## 📞 Support

Pour les problèmes:
1. Consulter la documentation
2. Vérifier les logs du navigateur (F12)
3. Vérifier les logs du backend
4. Ouvrir une issue avec les détails

---

**Status:** ✅ Production-ready  
**Dernière mise à jour:** 2024-06-17  
**Version:** 1.0.0
