# Splits SoccerNet par match

Ce dossier contient les fichiers `train.txt`, `valid.txt` et `test.txt` générés localement.
Ils ne sont pas fournis dans l'archive, car ils dépendent du sous-ensemble SoccerNet réellement téléchargé.

Commande recommandée depuis la racine du projet :

```powershell
python scripts/create_splits.py --root data/SoccerNet --output-dir splits --train-ratio 0.70 --valid-ratio 0.15 --test-ratio 0.15 --seed 42 --complete-halves
```

Chaque ligne doit être un chemin de match relatif à `data/SoccerNet`, par exemple :

```text
england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley
```

Principe : aucun match ne doit apparaître dans plusieurs ensembles.
