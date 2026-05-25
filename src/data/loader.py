"""
Data loaders for SoccerNet Action Spotting
"""
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple
import torch
from torch.utils.data import Dataset


class SoccerNetDataset(Dataset):
    """
    Dataset for SoccerNet Action Spotting
    
    Loads game data and labels from SoccerNet directory structure
    """
    
    def __init__(self, 
                 root_dir: str,
                 split: str = "train",
                 game_dirs: List[str] = None):
        """
        Args:
            root_dir: Path to soccernet data directory
            split: 'train', 'valid', or 'test'
            game_dirs: Specific game directories to load (if None, discover automatically)
        """
        self.root_dir = Path(root_dir)
        self.split = split
        self.games = []
        self.labels_per_game = {}
        
        if game_dirs is None:
            self._discover_games()
        else:
            self.games = game_dirs
            
        self._load_labels()
    
    def _discover_games(self):
        """Discover game directories in the SoccerNet structure"""
        # Look for game directories (format: YYYY-MM-DD - HH-MM ...)
        for game_path in self.root_dir.rglob("*/Labels.json"):
            game_dir = game_path.parent
            self.games.append(str(game_dir))
    
    def _load_labels(self):
        """Load Labels.json from each game"""
        for game_dir in self.games:
            labels_file = Path(game_dir) / "Labels.json"
            
            if labels_file.exists():
                with open(labels_file, 'r') as f:
                    labels_data = json.load(f)
                    self.labels_per_game[game_dir] = labels_data
    
    def __len__(self):
        return len(self.games)
    
    def __getitem__(self, idx):
        """Get a game sample with its labels"""
        game_dir = self.games[idx]
        labels = self.labels_per_game.get(game_dir, {})
        
        return {
            'game_dir': game_dir,
            'labels': labels
        }
    
    def get_stats(self) -> Dict:
        """Get dataset statistics"""
        total_games = len(self.games)
        total_events = sum(
            len(labels.get('annotations', []))
            for labels in self.labels_per_game.values()
        )
        
        return {
            'total_games': total_games,
            'total_events': total_events,
            'avg_events_per_game': total_events / total_games if total_games > 0 else 0
        }


def load_game_data(game_dir: str) -> Dict:
    """
    Load all data from a single game directory
    
    Returns:
        Dictionary with 'labels' and other metadata
    """
    game_path = Path(game_dir)
    labels_file = game_path / "Labels.json"
    
    data = {}
    
    if labels_file.exists():
        with open(labels_file, 'r') as f:
            data['labels'] = json.load(f)
    
    data['game_path'] = str(game_path)
    data['game_name'] = game_path.name
    
    return data
