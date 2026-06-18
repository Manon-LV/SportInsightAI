# Guide Pratique: Implémenter les Solutions d'Imbalance

## 🎯 Résumé Rapide

Vous avez 3 niveaux d'implémentation selon votre temps disponible:

### **Niveau 1: Rapide (15 min) ⭐⭐⭐ RECOMMANDÉ**
Utiliser la config optimisée avec Mixup + Label Smoothing:

```bash
cd sportinsight_dense_anchor

# Analyser votre dataset pour obtenir les weights optimaux
python scripts/analyze_class_balance.py \
  --root path/to/soccernet \
  --split-file splits/train.txt \
  --generate-config

# Entraîner avec la config optimisée
python scripts/run_experiments.py configs/optimized_imbalance.yaml
```

### **Niveau 2: Intermédiaire (1h) ⭐⭐⭐**
Comme Niveau 1, mais affiner les hyperparamètres:

1. Copier la config généré et l'ajuster:
   - Augmenter `mixup.apply_prob` de 0.5 → 0.7 si très imbalancé
   - Augmenter `label_smoothing.alpha` de 0.1 → 0.15
   - Augmenter epochs de 40 → 50

2. Réentraîner et comparer les résultats

### **Niveau 3: Avancé (2h+) ⭐⭐⭐**
Combiner plusieurs techniques:

```yaml
loss:
  type: "asl"              # Asymmetric Loss (déjà dans optimized_imbalance.yaml)
  class_weights: [...]     # Auto-calculés

augmentation:
  enabled: true
  mixup:
    enabled: true
    alpha: 0.2
    apply_prob: 0.7        # Augmenter l'agressivité
  cutmix:
    enabled: true          # Ajouter CutMix pour plus de data augmentation
    apply_prob: 0.2
  label_smoothing:
    alpha: 0.15            # Augmenter légèrement

train:
  epochs: 50               # Plus d'epochs pour meilleure convergence
```

---

## 📋 Étapes Détaillées

### Étape 1: Analyser votre Dataset

```bash
python scripts/analyze_class_balance.py \
  --root path/to/soccernet \
  --split-file splits/train.txt \
  --generate-config
```

**Output attendu:**
```
📊 Analyse du Dataset

✓ Dataset chargé: 12543 windows

📈 DISTRIBUTION DES CLASSES

Total d'exemples avec action: 3421

Classe            Décompte    Pourcentage    Poids
Goal              1245        36.4%          1.000
Corner            1850        54.1%          0.672
Yellow card       300         8.8%           4.150
Red card          26          0.8%           47.885

Ratio déséquilibre (max/min): 71.2x

⚙️ POIDS RECOMMANDÉS POUR LA LOSS
class_weights: [1.0, 0.672, 4.15, 47.885]

💡 RECOMMANDATIONS
⚠️ IMBALANCE TRÈS IMPORTANT (>5x)
   → Utiliser Asymmetric Loss (ASL) - prévu dans optimized_imbalance.yaml
   → Ajouter Mixup + Label Smoothing - déjà prévu
   → Considérer CutMix pour augmentation temporelle
```

### Étape 2: Utiliser la Config Optimisée

La config `configs/optimized_imbalance.yaml` contient déjà:

✅ **Loss:**
- Type: Asymmetric Loss (meilleur pour multi-label imbalance)
- Class weights: À remplir avec vos données
- Smooth L1 regression

✅ **Augmentation:**
- Mixup: Mélange linéaire d'exemples (50% du temps)
- Label Smoothing: Cible softer (10% lissage)
- CutMix: Désactivé par défaut (trop agressif)

✅ **Training:**
- 40 epochs (ajuster si besoin)
- Learning rate adapté (3e-4)
- Gradient clipping pour stabilité

### Étape 3: Entraîner

```bash
# Mode simple: utiliser la config par défaut
python scripts/run_experiments.py configs/optimized_imbalance.yaml

# Mode personnalisé: créer votre propre config
cp configs/optimized_imbalance.yaml configs/my_optimized.yaml
# Éditer my_optimized.yaml avec vos hyperparamètres
python scripts/run_experiments.py configs/my_optimized.yaml
```

### Étape 4: Comparer avec Baseline

```bash
# Voir tous les résultats d'entraînement
python scripts/compare_experiments.py

# Ou générer un rapport détaillé
python scripts/compare_experiments.py --output report.txt
```

---

## 🔧 Configuration: Explication Détaillée

### Loss Configuration

```yaml
loss:
  type: "asl"               # Asymmetric Loss pour imbalance
  class_weights: [1.0, 0.672, 4.15, 47.885]  # Auto-calculés
  gamma_pos: 1.0            # Contrôle la pénalité sur les positifs mal prédits
  gamma_neg: 4.0            # Contrôle la pénalité sur les négatifs (plus haut = plus agressif)
  prob_shift: 0.05          # Margin de confiance pour les négatifs (0-1)
```

**Quand ajuster:**
- Classes très rares (Red Card): Augmenter `gamma_neg` (4 → 6)
- Trop de false positives: Augmenter `prob_shift` (0.05 → 0.1)
- Performance instable: Diminuer `gamma_neg` (4 → 2)

### Augmentation Configuration

```yaml
augmentation:
  enabled: true                    # Activer/désactiver tout
  
  mixup:
    enabled: true
    alpha: 0.2                     # Beta(0.2, 0.2): petites valeurs = peu de mélange
    apply_prob: 0.5                # Appliquer 50% du temps (0 = jamais, 1 = toujours)
  
  cutmix:                          # Remplacement temporel (optionnel)
    enabled: false                 # Commencer désactivé
    apply_prob: 0.3
  
  label_smoothing:                 # Toujours recommandé
    alpha: 0.1                     # 10% de lissage (0.05-0.2 typique)
```

**Ajustements selon votre imbalance:**

| Imbalance | alpha_mixup | mixup_prob | label_smooth | cutmix |
|-----------|------------|-----------|--------------|--------|
| Faible (<2x) | 0.2 | 0.3 | 0.05 | false |
| Modéré (2-5x) | 0.2 | 0.5 | 0.1 | false |
| Sévère (>5x) | 0.15 | 0.7 | 0.15 | true |

### Training Configuration

```yaml
train:
  epochs: 40                       # Augmenter si imbalance sévère
  batch_size: 16                   # Garder si assez de mémoire
  lr: 0.0003                       # Apprendre lent pour stabilité
  weight_decay: 0.0001             # Régularisation L2
  grad_clip_norm: 1.0              # Éviter les gradients explosifs
  validate_every: 1                # Valider chaque epoch
```

---

## 📊 Résultats Attendus

### Avec Mixup + Label Smoothing

**Typiquement:**
- ↓ Overfitting: gap généralization réduit de 20-40%
- ↑ Stabilité: moins de variance entre runs
- ↑ Classes rares: meilleur recall sur Red Card, Yellow Card

**Exemple:**
```
AVANT (Baseline):
  Train loss: 0.006
  Val loss: 0.036
  Gap: 0.030 (300% de surapprentissage)
  
APRÈS (Mixup + Label Smoothing):
  Train loss: 0.008
  Val loss: 0.027
  Gap: 0.019 (150% surapprentissage - réduit de moitié!)
```

### Avec Asymmetric Loss + Class Weights

**Typiquement:**
- ↑ Recall sur classes rares: +15-25%
- ↓ False positives: -10-15%
- Meilleur équilibre precision/recall

---

## 🐛 Dépannage

### Problème: Training instable (loss oscille)
**Solutions:**
1. ↓ Learning rate: 3e-4 → 1e-4
2. ↓ Mixup alpha: 0.2 → 0.1
3. ↑ Grad clip norm: 1.0 → 0.5

### Problème: Convergence lente
**Solutions:**
1. ↑ Epochs: 40 → 60
2. ↑ Mixup apply_prob: 0.5 → 0.3 (moins d'augmentation)
3. Vérifier que class_weights sont corrects

### Problème: Overfitting persiste
**Solutions:**
1. ↑ Label smoothing alpha: 0.1 → 0.2
2. ↑ Mixup alpha: 0.2 → 0.3
3. ↓ Dropout: 0.20 → 0.30
4. Ajouter CutMix: `cutmix.enabled: true`

### Problème: Classes rares ignorées
**Solutions:**
1. Vérifier class_weights (très élevés pour classes rares?)
2. ↑ Epochs pour plus de temps d'apprentissage
3. ↑ gamma_neg dans ASL: 4 → 6

---

## 🚀 Commandes Utiles

```bash
# Analyser imbalance et générer config
python scripts/analyze_class_balance.py --root path/to/data --generate-config

# Entraîner
python scripts/run_experiments.py configs/optimized_imbalance.yaml

# Comparer tous les résultats
python scripts/compare_experiments.py

# Tester sur un mini dataset (sanity check)
python scripts/sanity_check.py

# Évaluer un checkpoint spécifique
python scripts/evaluate_predictions.py \
  --checkpoint runs/optimized_imbalance/best.pt \
  --split-file splits/test.txt
```

---

## 📚 Pour Aller Plus Loin

### Techniques Avancées (Non implémentées yet)

1. **Focal Loss Dynamique:** Adapter gamma_pos/neg par epoch
2. **Cost-Sensitive Learning:** Multiplier par loss_weight par exemple
3. **Bootstrapping:** Ré-échantillonner avec remplacement intelligent
4. **Curriculum Learning:** Commencer facile, augmenter la difficulté

### Lectures Recommandées

- ✅ [Focal Loss] Lin et al., 2017
- ✅ [Mixup] Zhang et al., 2017  
- ✅ [Asymmetric Loss] Ridnik et al., 2021
- 📖 [Class-Balanced Loss] Cui et al., 2019
- 📖 [OHEM] Shrivastava et al., 2016

---

## ✅ Checklist Finale

- [ ] Analyser le dataset avec `analyze_class_balance.py`
- [ ] Copier les class_weights dans la config
- [ ] Choisir le niveau d'implémentation (1, 2, ou 3)
- [ ] Entraîner avec la config optimisée
- [ ] Comparer avec baseline: `python scripts/compare_experiments.py`
- [ ] Valider: overfitting réduit? Recall sur classes rares amélioré?
- [ ] Fine-tuner les hyperparamètres selon vos résultats
- [ ] Publier les résultats! 🎉
