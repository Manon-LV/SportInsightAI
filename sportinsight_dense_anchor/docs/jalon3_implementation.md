# Jalon 3 — démarrage technique

## Décision d'interface

L'interface cible est une application web structurée en deux parties :

- backend FastAPI pour l'inférence et le stockage des runs ;
- frontend Vue 3 + TypeScript + Quasar pour une console d'analyse sportive.

Le prototype alpha reste compatible avec les features SoccerNet préextraites : l'utilisateur sélectionne un match, mais le modèle reçoit des fenêtres de features `L x 512` issues de `1_ResNET_PCA512.npy` et `2_ResNET_PCA512.npy`.

## Contrat d'entrée

Pour le Jalon 3, l'entrée API est :

```json
{
  "match_dir": "data/SoccerNet/example_match",
  "checkpoint": "runs/dense_anchor/best.pt",
  "half": "both",
  "score_threshold": 0.3,
  "nms_radius_sec": 6.0,
  "selected_classes": ["Goal", "Corner", "Yellow card", "Red card"],
  "device": "auto"
}
```

## Changements modèle

`DenseAnchorSpotter` supporte maintenant :

```yaml
model:
  use_projection: false
```

Dans ce mode, la projection `Linear(512 -> 256)` est retirée et remplacée par :

```text
LayerNorm(512) -> Dropout
```

La baseline reste rétrocompatible avec les checkpoints existants, car `use_projection` vaut `true` par défaut.

## Fichiers ajoutés

```text
configs/no_projection.yaml
configs/classes_10.yaml
apps/api/
apps/web/
docs/jalon3_implementation.md
```

## Ordre de travail recommandé

1. Lancer l'API et vérifier `/health`.
2. Lancer le frontend et vérifier que la page `Analyst Room` s'affiche.
3. Tester une inférence avec le checkpoint existant `runs/dense_anchor/best.pt`.
4. Entraîner `configs/no_projection.yaml` dans `runs/dense_anchor_no_projection`.
5. Comparer baseline et no-projection avec les métriques existantes.

## Refonte UX - interface simplifiée

L'interface Jalon 3 a été simplifiée pour réduire la charge cognitive utilisateur :

- le parcours principal est maintenant guidé : choisir/charger un match, analyser, lire le résumé et la timeline ;
- les paramètres techniques (`checkpoint`, seuil, NMS, import JSON, classes visibles) sont regroupés dans un panneau **Paramètres avancés** ;
- la timeline n'affiche plus tous les labels en permanence afin d'éviter le chevauchement visuel ;
- le rapport automatique est placé avant la timeline pour donner immédiatement les statistiques utiles ;
- la liste complète des événements est accessible dans une fenêtre dédiée, tandis que le panneau principal affiche seulement l'événement sélectionné.

Cette organisation conserve l'architecture FastAPI + Vue/Quasar, mais rapproche l'expérience d'un prototype produit destiné à un entraîneur ou analyste sportif.
