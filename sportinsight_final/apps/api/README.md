# SportInsight API

Lancement depuis la racine du dépôt :

```bash
pip install -e .
pip install fastapi uvicorn pydantic
uvicorn apps.api.main:app --reload --port 8000
```

Endpoints principaux :

- `GET /health`
- `GET /matches?root=data/SoccerNet`
- `GET /checkpoints?root=runs`
- `POST /inference/run`
- `GET /runs/{run_id}/events`
- `GET /runs/{run_id}/summary`

## Prévisualisation vidéo des actions

L'API peut maintenant servir les vidéos locales associées à un match SoccerNet.
Pour que la prévisualisation fonctionne dans l'interface, place les vidéos dans le dossier du match, à côté de `Labels-v2.json` et des features `.npy` :

```text
match_dir/
├── Labels-v2.json
├── 1_ResNET_PCA512.npy
├── 2_ResNET_PCA512.npy
├── 1.mp4   # ou 1.mkv
└── 2.mp4   # ou 2.mkv
```

Endpoints utiles :

```text
GET /media/video/availability?match_dir=...
GET /media/video?match_dir=...&half=1
GET /media/clip?match_dir=...&half=1&timestamp=790.0&before_sec=10&after_sec=10
```

Le lecteur de l'interface utilise la vidéo complète de la mi-temps et se positionne automatiquement autour du timestamp de l'action. Les fichiers `.mp4` sont recommandés pour la démonstration navigateur. Les `.mkv` peuvent nécessiter une conversion selon le navigateur.
