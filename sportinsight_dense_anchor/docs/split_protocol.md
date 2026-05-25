# Protocole de split train / validation / test

À partir de cette version, l'entraînement peut utiliser un split **par match** au lieu d'un split aléatoire par fenêtres.

## Pourquoi changer ?

Le split par fenêtres est utile pour un premier debug, mais il peut placer deux fenêtres du même match dans train et validation. Avec des fenêtres de 120 s et un stride de 60 s, les fenêtres se recouvrent fortement. Les métriques deviennent donc trop optimistes.

Le protocole recommandé est :

- `train.txt` : matchs utilisés pour apprendre les poids du modèle ;
- `valid.txt` : matchs utilisés pour choisir le checkpoint, le seuil et la NMS ;
- `test.txt` : matchs jamais utilisés pendant l'entraînement ou le réglage, réservés à l'évaluation finale et aux inférences de démonstration dans l'interface.

## Créer les fichiers de split

Depuis la racine du projet :

```powershell
python scripts/create_splits.py `
  --root data/SoccerNet `
  --output-dir splits `
  --train-ratio 0.70 `
  --valid-ratio 0.15 `
  --test-ratio 0.15 `
  --seed 42 `
  --complete-halves
```

Le script génère :

```text
splits/train.txt
splits/valid.txt
splits/test.txt
splits/summary.json
splits/integrity.json
```

Chaque ligne contient un chemin relatif à `data/SoccerNet`, par exemple :

```text
england_epl/2014-2015/2015-02-21 - 18-00 Chelsea 1 - 1 Burnley
```

## Entraîner avec le split propre

La configuration `configs/default.yaml` pointe maintenant vers :

```yaml
data:
  train_split_file: "splits/train.txt"
  val_split_file: "splits/valid.txt"
  test_split_file: "splits/test.txt"
```

Commande :

```powershell
python -m sportinsight.train --config configs/default.yaml
```

Le fichier `runs/dense_anchor/split_info.json` est écrit automatiquement pour documenter le protocole utilisé.

## Évaluer sur le test

```powershell
python scripts/evaluate_dataset_metrics.py `
  --checkpoint runs/dense_anchor/best.pt `
  --root data/SoccerNet `
  --split-file splits/test.txt `
  --output-dir runs/dense_anchor/eval_test `
  --score-threshold 0.05
```

## Interface

L'interface charge automatiquement les matchs listés dans `splits/test.txt` via l'API :

```text
GET /splits/test/matches
```

Le bouton **Analyser le match** travaille donc prioritairement sur un match du split test.
