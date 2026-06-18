# 🎬 Comment utiliser l'interface web

## ⏱️ 30 secondes pour démarrer

### Ouvrir 2 terminaux

**Terminal 1 (Backend):**
```bash
cd sportinsight_final
uvicorn apps.api.main:app --reload
```

**Terminal 2 (Frontend):**
```bash
cd sportinsight_final/apps/web
npm run dev
```

**Navigateur:** http://localhost:5173

---

## 🎯 Cas d'usage 1: Uploader et analyser vos vidéos

### Étape 1: Cliquer sur "Uploader une vidéo"
```
Menu Principal
├── [Analyser un match]   [Uploader une vidéo] ← CLIQUER ICI
```

### Étape 2: Remplir le formulaire
```
Nom du match:      PSG vs Lyon
Mi-temps 1:        [Glisser/Cliquer pour fichier]
Mi-temps 2:        [Glisser/Cliquer pour fichier]
Checkpoint:        best ▼
```

### Étape 3: Cliquer "Uploader et analyser"
```
Barre de progression:
1️⃣ Création du job       ✅
2️⃣ Upload mi-temps 1    ✅
3️⃣ Upload mi-temps 2    ✅
4️⃣ Finalisation         ✅
5️⃣ Extraction features  ⏳ (5-15 minutes)
```

### Étape 4: Voir les résultats
```
Une fois terminé:
[Analyser maintenant] ← Cliquer pour voir les événements
```

---

## 📊 Cas d'usage 2: Analyser un match SoccerNet

### Étape 1: Cliquer sur "Analyser un match"
```
Menu Principal
├── [Analyser un match] ← CLIQUER ICI   [Uploader une vidéo]
```

### Étape 2: Sélectionner le split
```
Splits disponibles:
- train (800 matchs)
- test  (500 matchs)
- valid (100 matchs)
```

### Étape 3: Choisir un match
```
Liste des matchs:
- PSG vs Monaco
- Lyon vs OM
- Marseille vs Nice
- ...
```

### Étape 4: Lancer l'inférence
```
Checkpoint: best ▼
[Analyser] ← Cliquer
```

### Étape 5: Voir les résultats
```
Timeline interactive + EventList
```

---

## 🎨 Interface - Explication visuelle

### Menu Principal
```
┌─────────────────────────────────────────────────┐
│              SportInsight AI                    │
│                                                 │
│  ┌──────────────────┐  ┌────────────────────┐  │
│  │   Analyser       │  │   Uploader une     │  │
│  │  un match        │  │    vidéo           │  │
│  │                  │  │                    │  │
│  │ Matchs           │  │ Vos propres vidéos │  │
│  │ SoccerNet        │  │ (mi-temps 1 + 2)   │  │
│  │                  │  │                    │  │
│  │ [Continuer]      │  │ [Continuer]        │  │
│  └──────────────────┘  └────────────────────┘  │
│                                                 │
│  • Modèles pré-entraînés                       │
│  • Upload sécurisé                             │
│  • Rapide et efficace                          │
└─────────────────────────────────────────────────┘
```

### Upload Interface
```
┌─────────────────────────────────────────┐
│  📤 Upload de Vidéo de Match            │
├─────────────────────────────────────────┤
│                                         │
│ Nom du match:                           │
│ [PSG vs Lyon          ]                 │
│                                         │
│ Mi-temps 1:                             │
│ ╔═══════════════════════════════════╗  │
│ ║  📁 Glisser/Cliquer               ║  │
│ ║     pour sélectionner              ║  │
│ ╚═══════════════════════════════════╝  │
│                                         │
│ Mi-temps 2:                             │
│ ╔═══════════════════════════════════╗  │
│ ║  📁 Glisser/Cliquer               ║  │
│ ║     pour sélectionner              ║  │
│ ╚═══════════════════════════════════╝  │
│                                         │
│ Checkpoint:                             │
│ [best                    ▼]             │
│                                         │
│ [Annuler] [Uploader et analyser]       │
└─────────────────────────────────────────┘
```

### Progression
```
┌──────────────────────────────────────────┐
│ 📋 Progression                           │
├──────────────────────────────────────────┤
│                                          │
│ 1️⃣ Création du job        ✅            │
│ 2️⃣ Upload mi-temps 1      ✅            │
│ 3️⃣ Upload mi-temps 2      ✅            │
│ 4️⃣ Finalisation           ✅            │
│ 5️⃣ Extraction features    ⏳ 45%        │
│                                          │
│ ████████████░░░░░░░░░░░░░░░ 45%         │
│                                          │
│ Extraction des features ResNET...       │
│ Env. 8 minutes restantes                │
│                                          │
│ Job ID: 550e8400-e29b-41d4-a716...    │
│ Match Dir: /storage/uploads/550e...    │
│                                          │
│ [Copier ID] [Rafraîchir]                │
│                                          │
│ [Analyser maintenant]    ← Une fois ✅  │
└──────────────────────────────────────────┘
```

### Résultats
```
┌─────────────────────────────────────────────────┐
│ 📊 Résultats d'analyse                          │
├─────────────────────────────────────────────────┤
│                                                 │
│ Timeline Interactive:                           │
│ ─────────────────────────────────────────────   │
│ 0:00  🟢 Shot               0:45                │
│       📍 Shot Detected at t=45s                 │
│       Confidence: 92%                           │
│                                                 │
│ 3:20  🔴 Tackle             3:20                │
│       📍 Tackle at t=200s                       │
│       Confidence: 85%                           │
│                                                 │
│ 15:45 🟡 Goal              15:45                │
│       📍 Goal!                                  │
│       Confidence: 98%                           │
│                                                 │
│ Événements (60 total):                          │
│ ─────────────────────────────────────────────   │
│ ☐ Shot     - 25 événements - Confiance 90%     │
│ ☐ Tackle   - 18 événements - Confiance 83%     │
│ ☐ Pass     - 10 événements - Confiance 87%     │
│ ☐ Goal     -  2 événements - Confiance 99%     │
│ ☐ Other    -  5 événements - Confiance 75%     │
│                                                 │
│ [Retour au menu] [Nouvelle analyse]             │
└─────────────────────────────────────────────────┘
```

---

## 🎬 Formats vidéo supportés

✅ Supporté:
- MP4
- MKV
- WebM
- MOV
- AVI

Chaque vidéo peut durer:
- De quelques secondes (test) à 90 minutes (complet)

---

## ⚡ Vitesse estimée

| Opération | Durée |
|-----------|-------|
| Upload 100 MB | 10-30 sec |
| Extraction features | 5-30 min |
| Inférence | 5-10 sec |
| Affichage résultats | Instantané |
| **Total** | **15-45 min** |

---

## 🔴 Erreurs possibles et solutions

### "L'API ne répond pas"
```
❌ Error: Failed to connect to http://localhost:8000

✅ Solution:
Terminal 1 → Vérifier que l'API est lancée
Vérifier le port 8000 est libre
Relancer: uvicorn apps.api.main:app --reload
```

### "Port 5173 déjà utilisé"
```
❌ Error: EADDRINUSE: address already in use :::5173

✅ Solution:
npm run dev -- --port 3000
Accéder à http://localhost:3000
```

### "npm modules manquants"
```
❌ Error: Cannot find module 'vue'

✅ Solution:
cd apps/web
npm install
npm run dev
```

### "Fichier vidéo non accepté"
```
❌ Error: Unsupported file format

✅ Solution:
Vérifier le format vidéo (MP4, MKV, etc.)
Vérifier que le fichier n'est pas corrompu
Réenregistrer avec FFmpeg si besoin
```

---

## 💾 Où sont stockés les fichiers?

```
apps/api/storage/uploads/
└── {job_id}/                    # ID unique du job
    └── {match_name}/            # Nom du match
        ├── 1.mp4               # Vidéo originale mi-temps 1
        ├── 2.mp4               # Vidéo originale mi-temps 2
        ├── 1_ResNET_TF2_PCA512.npy  # Features extraites
        └── 2_ResNET_TF2_PCA512.npy  # Features extraites
```

---

## 🔍 Debugging

### Vérifier l'API
```bash
curl http://localhost:8000/health

# Réponse attendue:
# {"status":"ok","service":"sportinsight-api"}
```

### Vérifier les checkpoints
```bash
curl http://localhost:8000/checkpoints

# Réponse attendue:
# [{"id":"best","path":"...","name":"Best Model"}]
```

### Voir les logs en détail
```bash
# Terminal 1 - API:
uvicorn apps.api.main:app --reload --log-level debug

# Terminal 2 - Web (F12 dans navigateur):
F12 → Console → Voir les logs Vue.js
```

---

## 🎓 Workflow complet - Étape par étape

```
1. Démarrer l'API
   └─ Terminal 1: uvicorn apps.api.main:app --reload

2. Démarrer le web
   └─ Terminal 2: npm run dev

3. Ouvrir le navigateur
   └─ http://localhost:5173

4. Menu principal s'affiche
   └─ Choisir: "Uploader" ou "Analyser"

5. UPLOADER:
   ├─ Remplir nom du match
   ├─ Sélectionner vidéos
   ├─ Cliquer "Uploader"
   ├─ Attendre progression
   ├─ Voir "Prêt pour analyse"
   └─ Cliquer "Analyser"

6. ANALYSER:
   ├─ Sélectionner split
   ├─ Choisir match
   ├─ Lancer inférence
   └─ Voir résultats

7. Voir les résultats:
   ├─ Timeline interactive
   ├─ Liste des événements
   ├─ Graphiques statistiques
   └─ Possibilité d'export (futur)
```

---

## 📚 Documentation complète

Pour plus de détails, voir:

- **WEB_QUICKSTART.md** - Démarrage rapide 30 sec
- **WEB_INTERFACE_GUIDE.md** - Guide détaillé avec UI
- **README_WEB.md** - Documentation technique
- **ARCHITECTURE.md** - Architecture système
- **STARTUP_CHECKLIST.md** - Checklist et troubleshooting
- **INTEGRATION_SUMMARY.md** - Résumé intégration

---

## 🚀 Tips & Tricks

1. **Raccourcis clavier:**
   - `F12` - Ouvrir console de développement
   - `Ctrl+R` - Rafraîchir la page
   - `Ctrl+Shift+Del` - Effacer cache

2. **Performance:**
   - Utiliser GPU pour extraction features (3-5x plus rapide)
   - Réduire la résolution vidéo si possible
   - Fermer les autres onglets

3. **Troubleshooting:**
   - Toujours vérifier les logs API
   - Consulter la console du navigateur (F12)
   - Vérifier la connexion réseau

4. **Après terminer:**
   - Les fichiers restent dans `storage/uploads`
   - Vous pouvez les analyser à nouveau
   - Supprimer manuellement si besoin

---

## ✨ Fonctionnalités actuelles

✅ Upload vidéo (MP4, MKV, WebM, etc.)
✅ Extraction features ResNET50
✅ Stockage local sécurisé
✅ Analyse SoccerNet
✅ Timeline interactive
✅ EventList détaillée
✅ Gestion des erreurs
✅ Suivi de progression

---

## 🎯 Prochaines étapes

1. **Immédiatement:** Tester l'upload avec une petite vidéo
2. **Ensuite:** Analyser les résultats
3. **Puis:** Configurer en production (optionnel)

---

## 🆘 Besoin d'aide?

1. **Consulter la documentation** - Voir fichiers .md
2. **Vérifier les logs** - Terminal API + Console navigateur
3. **Restart les services** - Utile pour 90% des problèmes
4. **Vérifier les ports** - 8000 (API) et 5173 (Web)

---

**Prêt à commencer? 🚀 Lancez les 2 terminaux et ouvrez http://localhost:5173**

Bon travail! 🎉
