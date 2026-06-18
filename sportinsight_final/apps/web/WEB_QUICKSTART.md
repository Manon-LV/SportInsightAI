# 🚀 Démarrage rapide - Interface Web

## 30 secondes pour commencer

### Terminal 1: Démarrer l'API
```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

**Vérifier:** http://localhost:8000/health

### Terminal 2: Démarrer l'interface web
```bash
cd sportinsight_final/apps/web
npm run dev
```

**Accéder:** http://localhost:5173

---

## 🎯 Utilisation

### 1️⃣ Menu principal
Vous verrez deux options:
- **Analyser un match** - Matches SoccerNet ou précédemment uploadés
- **Uploader une vidéo** - Vos propres vidéos

### 2️⃣ Cliquer sur "Uploader une vidéo"

### 3️⃣ Remplir le formulaire
1. Nom du match
2. Glisser-déposer mi-temps 1
3. Glisser-déposer mi-temps 2
4. Sélectionner le checkpoint
5. Cliquer "Uploader et analyser"

### 4️⃣ Suivre la progression
- ✅ Création du job
- ✅ Upload mi-temps 1
- ✅ Upload mi-temps 2
- ✅ Finalisation
- ✅ Extraction features (5-15 min)

### 5️⃣ Voir les résultats
- Cliquer "Analyser maintenant"
- Les événements s'affichent automatiquement

---

## 📦 Installation initiale (une seule fois)

```bash
cd sportinsight_final/apps/web
npm install
```

---

## ✅ Checklist

- [ ] Node.js 18+ installé (`node --version`)
- [ ] npm installé (`npm --version`)
- [ ] FFmpeg installé (`ffmpeg --version`)
- [ ] PyTorch installé
- [ ] API accessible sur port 8000
- [ ] Web accessible sur port 5173

---

## 🔧 Troubleshooting

### Port 5173 déjà utilisé
```bash
npm run dev -- --port 3000
# Puis accédez à http://localhost:3000
```

### npm packages manquants
```bash
npm install
npm run dev
```

### L'API ne répond pas
```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload --log-level debug
```

---

## 📊 Architecture

```
Client Web (Vue.js)
      ↓
Service API (axios/fetch)
      ↓
Backend API (FastAPI)
      ↓
Services (Upload, Features, Inference)
```

---

## 🎨 Personnalisation

### Changer la couleur de thème
Modifier dans les composants Vue:
```vue
<style scoped>
.cyan { /* Cyan par défaut */ }
</style>
```

### Changer les endpoints
Modifier `.env`:
```env
VITE_API_BASE_URL=http://localhost:8000
```

### Ajouter plus de fonctionnalités
1. Créer un nouveau composant dans `src/components/`
2. L'importer dans `MainMenu.vue`
3. Ajouter les fonctions API dans `services/api.ts`

---

## 📈 Performance

- Temps de chargement: < 2s
- Upload UI: < 100ms réponse
- Tous les appels sont asynchrones (non-bloquant)

---

## 🔐 Notes de sécurité

- Les vidéos ne quittent jamais votre machine
- Stockage local uniquement
- HTTPS recommandé en production

---

Pour plus d'informations: [WEB_INTERFACE_GUIDE.md](WEB_INTERFACE_GUIDE.md)
