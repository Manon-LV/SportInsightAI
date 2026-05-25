"""
Evaluation metrics for Action Spotting
"""
import numpy as np
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns


def compute_metrics(y_true, y_pred, average='weighted'):
    """
    Compute classification metrics
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        average: Averaging method ('weighted', 'macro', 'micro')
    
    Returns:
        Dictionary with metrics
    """
    metrics = {
        'accuracy': np.mean(y_true == y_pred),
        'precision': precision_score(y_true, y_pred, average=average, zero_division=0),
        'recall': recall_score(y_true, y_pred, average=average, zero_division=0),
        'f1': f1_score(y_true, y_pred, average=average, zero_division=0),
    }
    
    return metrics


def plot_confusion_matrix(y_true, y_pred, class_names=None, figsize=(8, 6)):
    """
    Plot confusion matrix
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: Names of classes
        figsize: Figure size
    """
    cm = confusion_matrix(y_true, y_pred)
    
    plt.figure(figsize=figsize)
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=class_names, yticklabels=class_names)
    plt.ylabel('True')
    plt.xlabel('Predicted')
    plt.title('Confusion Matrix')
    plt.tight_layout()
    
    return plt.gcf()


def compute_per_class_metrics(y_true, y_pred, class_names=None):
    """
    Compute per-class precision, recall, f1
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: Names of classes
    
    Returns:
        Dictionary with per-class metrics
    """
    precision = precision_score(y_true, y_pred, average=None, zero_division=0)
    recall = recall_score(y_true, y_pred, average=None, zero_division=0)
    f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    
    if class_names is None:
        class_names = [f'Class {i}' for i in range(len(precision))]
    
    metrics = {}
    for i, name in enumerate(class_names):
        metrics[name] = {
            'precision': precision[i],
            'recall': recall[i],
            'f1': f1[i]
        }
    
    return metrics
