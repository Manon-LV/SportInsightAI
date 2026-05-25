"""
Baseline models for Action Spotting
"""
import torch
import torch.nn as nn


class SimpleClassifier(nn.Module):
    """
    Simple baseline classifier for action spotting
    
    Input: Feature vectors or embeddings
    Output: Action/No-Action classification
    """
    
    def __init__(self, input_dim: int = 512, num_classes: int = 2, dropout: float = 0.3):
        """
        Args:
            input_dim: Dimension of input features
            num_classes: Number of action classes
            dropout: Dropout probability
        """
        super(SimpleClassifier, self).__init__()
        
        self.net = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor [batch_size, input_dim]
        
        Returns:
            Logits [batch_size, num_classes]
        """
        return self.net(x)


class TemporalClassifier(nn.Module):
    """
    Classifier with temporal modeling using LSTM
    
    Captures temporal context for action spotting
    """
    
    def __init__(self, 
                 input_dim: int = 512,
                 hidden_dim: int = 128,
                 num_classes: int = 2,
                 num_layers: int = 2,
                 dropout: float = 0.3):
        """
        Args:
            input_dim: Dimension of input features
            hidden_dim: Hidden dimension of LSTM
            num_classes: Number of action classes
            num_layers: Number of LSTM layers
            dropout: Dropout probability
        """
        super(TemporalClassifier, self).__init__()
        
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            dropout=dropout,
            batch_first=True
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
    
    def forward(self, x):
        """
        Forward pass
        
        Args:
            x: Input tensor [batch_size, seq_len, input_dim]
        
        Returns:
            Logits [batch_size, num_classes]
        """
        # LSTM forward
        lstm_out, (h_n, c_n) = self.lstm(x)
        
        # Use last hidden state
        last_hidden = h_n[-1]  # [batch_size, hidden_dim]
        
        # Classification
        logits = self.fc(last_hidden)
        
        return logits
