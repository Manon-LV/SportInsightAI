# Solutions pour le Déséquilibre des Données et l'Overfitting

## 🎯 Problème Identifié

Vous avez un **déséquilibre dramatique des classes** : beaucoup plus de sorties de balle que de cartons rouges.
Cela cause de l'**overfitting** où le modèle apprend trop bien les cas fréquents au détriment des cas rares.

---

## 📊 Stratégies Recommandées (Par Ordre de Priorité)

### 1. **STRATÉGIE IMMÉDIATE: Mixup + Focal Loss + Class Weights** ⭐⭐⭐

#### A. Utiliser Mixup au niveau des features
Mélanger linéairement les features pour créer des exemples intermédiaires:
```
x_mixed = λ * x_i + (1-λ) * x_j
target_mixed = λ * target_i + (1-λ) * target_j
```

**Avantages:**
- Force le modèle à généraliser en apprenant les transitions entre classes
- Réduit drastiquement l'overfitting
- Compatible avec votre architecture existante

#### B. Optimiser les Class Weights
Basés sur la formule: `weight = total_samples / (n_classes * class_frequency)`

Cela amplifie les gradients des classes rares lors de la rétropropagation.

---

### 2. **STRATÉGIE AVANCÉE: BalancedOversampling + OHEM** ⭐⭐⭐

Remplacer le simple oversample par un **BalancedGroupOversampler**:
- Garder tous les exemples positifs rares (Red Card, Yellow Card)
- Dupliquer intelligemment les exemples d'autres classes manquantes
- Ne pas créer de données artificielles triviales

---

### 3. **STRATÉGIE COMPLÉMENTAIRE: CutMix pour Augmentation Temporelle** ⭐⭐

Appliquer à la dimension temporelle (pour l'action spotting):
```
x_mixed[start:end] = x_i[start:end]
target_mixed[start:end] = target_i[start:end]
```

Cela crée des transitions réalistes entre deux actions.

---

### 4. **STRATÉGIE FINE-TUNING: Label Smoothing + Soft Targets** ⭐⭐

```
target_smoothed = target * (1 - α) + 0.5 * α
```

Où α ≈ 0.1. Cela:
- Réduit l'overfitting en empêchant la confiance à 100%
- Améliore la calibration du modèle
- Fonctionne bien avec Focal Loss

---

### 5. **STRATÉGIE AVANCÉE: Focal Loss avec Dynamique Threshold** ⭐

Adapter le seuil de décision par classe en fonction de la fréquence:
```
threshold_class = base_threshold * (max_freq / class_freq)
```

---

## 🔧 Implémentation Recommandée

### Étape 1: Ajouter Mixup au Dataset
→ Voir `data_augmentation.py` (à créer)

### Étape 2: Recalculer les Class Weights
```bash
python -c "
from sportinsight.data import find_game_dirs
from sportinsight.labels import load_events_from_labels

# Analyser votre dataset et afficher les weights recommandés
"
```

### Étape 3: Mettre à Jour la Config
Créer une nouvelle config `configs/optimized.yaml` avec:
- Loss type: `asl` (Asymmetric Loss est excellent pour multi-label imbalance)
- Imbalance strategy: `oversample` avec balanced sampler
- Label smoothing: `0.1`
- Mixup probability: `0.5`
- Mixup alpha: `0.2`

### Étape 4: Benchmark
Comparer les configs:
```bash
# Baseline
python scripts/run_experiments.py configs/default.yaml

# Avec optimisations
python scripts/run_experiments.py configs/optimized.yaml
```

---

## 📈 Ordre de Priorité pour l'Implémentation

1. **Jour 1:** Mixup + Optimized Class Weights (gain 5-15%)
2. **Jour 2:** Balanced Oversampling (gain 3-8%)
3. **Jour 3:** Label Smoothing (gain 2-5%)
4. **Jour 4+:** CutMix + Fine-tuning du Focal Loss

---

## 🎓 Références Théoriques

- **Focal Loss:** Lin et al., 2017 - "Focal Loss for Dense Object Detection"
- **Mixup:** Zhang et al., 2017 - "Mixup: Beyond Empirical Risk Minimization"
- **Asymmetric Loss:** Ridnik et al., 2021 - "Asymmetric Loss For Multi-Label Classification"
- **OHEM:** Shrivastava et al., 2016 - "Training Region-based Object Detectors with Online Hard Example Mining"

---

## ⚠️ Pièges à Éviter

❌ Ne pas sur-équilibrer (oversample x 10+) → overfitting artificiel
❌ Ne pas modifier lambda_reg sans raison → pertube les offsets temporels
❌ Combiner trop de techniques à la fois → impossible de savoir ce qui marche

---

## ✅ Checklist d'Optimisation

- [ ] Analyser la distribution réelle des classes
- [ ] Calculer les weights optimaux par classe
- [ ] Implémenter Mixup au niveau dataset
- [ ] Tester avec Asymmetric Loss
- [ ] Ajouter Label Smoothing (α=0.1)
- [ ] Valider sur l'ensemble de test
- [ ] Comparer avec la baseline

