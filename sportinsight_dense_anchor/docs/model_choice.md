# Choix du modèle — Dense Temporal Anchor Spotter

## Papier principal

L'implémentation est inspirée de :

**Soares, J. V. B. & Shah, A. — _Action Spotting using Dense Detection Anchors Revisited_, 2022.**

Le principe est d'effectuer une détection dense sur l'axe temporel. Chaque instant de la séquence de features est traité comme une ancre. Le modèle prédit :

- un score d'action par classe ;
- un offset temporel permettant de corriger le timestamp de l'ancre.

## Adaptation au projet

Le papier original utilise une architecture plus complète et plusieurs raffinements. Cette version garde le mécanisme essentiel tout en restant compatible avec le temps et le matériel du projet :

```text
SoccerNet ResNet PCA512 → U-Net 1D léger → classification + offset → NMS temporelle
```

## Pourquoi ce choix ?

- Compatible avec les features préextraites SoccerNet ;
- plus précis qu'une simple classification de fenêtres grâce à la régression d'offset ;
- moins coûteux qu'une solution end-to-end à partir des frames ;
- sortie directement exploitable dans l'interface : classe, timestamp, score.

## Loss

```text
L = λ_cls · FocalBCE + λ_reg · SmoothL1(offset)
```

La partie classification utilise une focal loss pondérée pour gérer le déséquilibre entre les actions rares et les très nombreux instants sans événement. La partie régression n'est calculée que sur les ancres positives.

## Paramètres recommandés

| Paramètre | Valeur initiale |
|---|---:|
| Feature FPS | 2 |
| Fenêtre | 120 s |
| Stride | 60 s |
| Rayon positif | 2 s |
| Rayon ignoré | 5 s |
| NMS | 6 s |
| Hidden dim | 256 |
| Learning rate | 3e-4 |
| Batch size | 16 |
| Epochs | 30 |

## Limite actuelle

La validation intégrée suit une séparation simple par fenêtres pour démarrer rapidement. Pour le rapport final, il faudra utiliser les splits officiels SoccerNet train / valid / test afin d'obtenir des métriques comparables à l'état de l'art.
