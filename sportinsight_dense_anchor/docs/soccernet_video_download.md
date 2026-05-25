# Téléchargement des vidéos SoccerNet

Le prototype SportInsight AI peut analyser les features préextraites `ResNET_PCA512.npy` sans vidéo. Pour afficher l'extrait vidéo d'une action dans l'interface, il faut aussi télécharger les fichiers vidéo SoccerNet dans les mêmes dossiers de match.

## Prérequis

1. Avoir accès aux vidéos SoccerNet après signature du NDA.
2. Avoir le mot de passe vidéo SoccerNet.
3. Installer les dépendances du projet :

```powershell
pip install -r requirements.txt
pip install -e .
```

Le package officiel `SoccerNet` est utilisé via `SoccerNet.Downloader.SoccerNetDownloader`.

## Option A — Télécharger depuis l'interface

1. Lancer le backend :

```powershell
uvicorn apps.api.main:app --reload --host 127.0.0.1 --port 8000
```

2. Lancer le frontend :

```powershell
cd apps/web
npm install
npm run dev
```

3. Ouvrir **Paramètres avancés** dans l'interface.
4. Dans **Téléchargement SoccerNet**, renseigner :
   - `Dossier cible` : `data/SoccerNet`
   - `Mot de passe SoccerNet NDA`
   - `Qualité vidéo` : `224p` recommandé
   - `Splits` : `train`, `valid`, `test`, ou un match unique.
5. Cliquer sur **Télécharger vidéos**.

## Option B — Télécharger en ligne de commande

### Télécharger toutes les vidéos 224p des splits train/valid/test

```powershell
python scripts/download_soccernet_videos.py `
  --root data/SoccerNet `
  --password "MOT_DE_PASSE_NDA" `
  --resolution 224p `
  --split train valid test
```

### Télécharger un seul match

```powershell
python scripts/download_soccernet_videos.py `
  --root data/SoccerNet `
  --password "MOT_DE_PASSE_NDA" `
  --resolution 224p `
  --game "england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley"
```

### Utiliser une variable d'environnement au lieu de passer le mot de passe

```powershell
$env:SOCCERNET_PASSWORD="MOT_DE_PASSE_NDA"
python scripts/download_soccernet_videos.py --root data/SoccerNet --resolution 224p --split train valid test
```

## Structure attendue après téléchargement

```text
data/SoccerNet/england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley/
├── Labels-v2.json
├── 1_ResNET_PCA512.npy
├── 2_ResNET_PCA512.npy
├── 1_224p.mkv
└── 2_224p.mkv
```

L'interface détecte automatiquement les noms suivants :

```text
1_224p.mkv, 2_224p.mkv
1_720p.mkv, 2_720p.mkv
1.mp4, 2.mp4
1.mkv, 2.mkv
```

## Important pour le navigateur

Les vidéos SoccerNet sont souvent en `.mkv`. Certains navigateurs ne les lisent pas directement. Pour une démo stable, deux options existent :

1. installer `ffmpeg` et utiliser l'endpoint `/media/clip`, qui génère un extrait `.mp4` autour de l'action ;
2. convertir les fichiers `.mkv` en `.mp4` avant la démo.

Exemple de conversion :

```powershell
ffmpeg -i "1_224p.mkv" -c:v libx264 -preset veryfast -crf 23 -c:a aac "1.mp4"
ffmpeg -i "2_224p.mkv" -c:v libx264 -preset veryfast -crf 23 -c:a aac "2.mp4"
```
