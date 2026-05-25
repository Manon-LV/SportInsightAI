#================================================================================
#Imports
#================================================================================

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

from src.models.baseline import SimpleClassifier, TemporalClassifier
from src.utils.metrics import compute_metrics

#================================================================================
#Fonctions
#================================================================================

def main(args):
    """Main training function"""
    
    # Configuration
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Device: {device}")
    
    # Set random seeds
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    
    # Generate synthetic data for demonstration
    print(f"\nGenerating {args.n_samples} samples with {args.n_features} features...")
    X_data = np.random.randn(args.n_samples, args.n_features).astype(np.float32)
    y_data = np.random.randint(0, 2, args.n_samples)
    
    # Normalize features
    scaler = StandardScaler()
    X_normalized = scaler.fit_transform(X_data)
    
    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X_normalized, y_data, test_size=args.test_size, random_state=args.seed
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train, y_train, test_size=0.2, random_state=args.seed
    )
    
    print(f"  - Train: {X_train.shape[0]} samples")
    print(f"  - Val: {X_val.shape[0]} samples")
    print(f"  - Test: {X_test.shape[0]} samples")
    
    # Create tensors
    X_train_tensor = torch.from_numpy(X_train).to(device)
    y_train_tensor = torch.from_numpy(y_train).long().to(device)
    X_val_tensor = torch.from_numpy(X_val).to(device)
    y_val_tensor = torch.from_numpy(y_val).long().to(device)
    X_test_tensor = torch.from_numpy(X_test).to(device)
    y_test_tensor = torch.from_numpy(y_test).long().to(device)
    
    # Create model
    print(f"\nCreating {args.model} model...")
    if args.model == 'simple':
        model = SimpleClassifier(
            input_dim=args.n_features,
            num_classes=2,
            dropout=args.dropout
        ).to(device)
    else:
        model = TemporalClassifier(
            input_dim=args.n_features,
            hidden_dim=args.hidden_dim,
            num_classes=2,
            dropout=args.dropout
        ).to(device)
    
    # Loss and optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr)
    
    # Create DataLoader
    train_dataset = TensorDataset(X_train_tensor, y_train_tensor)
    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    
    # Training loop
    print(f"\nTraining for {args.epochs} epochs...")
    best_val_acc = 0
    train_losses = []
    val_accuracies = []
    
    for epoch in range(args.epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
        
        train_loss /= len(train_loader)
        train_losses.append(train_loss)
        
        # Validation phase
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val_tensor)
            val_preds = torch.argmax(val_outputs, dim=1)
            val_acc = (val_preds == y_val_tensor).float().mean().item()
            val_accuracies.append(val_acc)
            
            if val_acc > best_val_acc:
                best_val_acc = val_acc
                if args.save_checkpoint:
                    ckpt_dir = Path("checkpoints")
                    ckpt_dir.mkdir(exist_ok=True)
                    ckpt_path = ckpt_dir / f"best_model_{args.model}.pth"
                    torch.save(model.state_dict(), ckpt_path)
        
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{args.epochs} - Loss: {train_loss:.4f} - Val Acc: {val_acc:.4f}")
    
    # Evaluation
    print("\n" + "=" * 50)
    print("EVALUATION")
    print("=" * 50)
    
    model.eval()
    with torch.no_grad():
        # Predictions
        train_outputs = model(X_train_tensor)
        train_preds = torch.argmax(train_outputs, dim=1).cpu().numpy()
        
        test_outputs = model(X_test_tensor)
        test_preds = torch.argmax(test_outputs, dim=1).cpu().numpy()
    
    # Metrics
    train_metrics = compute_metrics(y_train, train_preds)
    test_metrics = compute_metrics(y_test, test_preds)
    
    print("\nTrain Metrics:")
    for key, value in train_metrics.items():
        print(f"  {key}: {value:.4f}")
    
    print("\nTest Metrics:")
    for key, value in test_metrics.items():
        print(f"  {key}: {value:.4f}")
    
    print("\nClassification Report (Test):")
    print(classification_report(y_test, test_preds, target_names=['No Action', 'Action']))
    
    # Save results
    if args.save_results:
        results_dir = Path("experiments")
        results_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {
            'model': args.model,
            'timestamp': timestamp,
            'train_metrics': train_metrics,
            'test_metrics': test_metrics,
            'hyperparameters': {
                'epochs': args.epochs,
                'batch_size': args.batch_size,
                'learning_rate': args.lr,
                'dropout': args.dropout
            }
        }
        
        results_file = results_dir / f"results_{args.model}_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {results_file}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train baseline model for Action Spotting')
    
    # Model arguments
    parser.add_argument('--model', type=str, default='simple', choices=['simple', 'temporal'],
                       help='Model architecture')
    parser.add_argument('--n-features', type=int, default=512, help='Input feature dimension')
    parser.add_argument('--hidden-dim', type=int, default=128, help='Hidden dimension for temporal model')
    parser.add_argument('--dropout', type=float, default=0.3, help='Dropout probability')
    
    # Training arguments
    parser.add_argument('--epochs', type=int, default=50, help='Number of training epochs')
    parser.add_argument('--batch-size', type=int, default=32, help='Batch size')
    parser.add_argument('--lr', type=float, default=0.001, help='Learning rate')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    
    # Data arguments
    parser.add_argument('--n-samples', type=int, default=2000, help='Number of samples to generate')
    parser.add_argument('--test-size', type=float, default=0.2, help='Test set size')
    
    # Output arguments
    parser.add_argument('--save-checkpoint', action='store_true', help='Save best model checkpoint')
    parser.add_argument('--save-results', action='store_true', help='Save results to JSON')
    
    args = parser.parse_args()
    main(args)
