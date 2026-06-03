# SportInsight Analyst Room

Interface finale choisie : Vue 3 + TypeScript + Quasar.

Lancement :

```bash
cd apps/web
npm install
npm run dev
```

Par défaut, le frontend appelle l'API sur `http://localhost:8000`.
Pour modifier l'URL :

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```


## Workflow Jalon 3 recommandé

1. Lancer le frontend.
2. Cliquer sur **Charger la démo JSON propre** pour vérifier la timeline sans relancer l'IA.
3. Vérifier que les 19 événements de `public/demo_predictions_clean.json` apparaissent.
4. Lancer ensuite l'API FastAPI et cliquer sur **Analyser** pour exécuter l'inférence réelle.

Valeurs par défaut utilisées dans l'interface :

- `score_threshold = 0.70`
- `nms_radius_sec = 6.0`
- classes affichées par défaut : `Goal`, `Corner`, `Yellow card`
- `Red card` reste disponible dans les filtres, mais n'est pas activée par défaut.
