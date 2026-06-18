from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional
import numpy as np
import cv2

REPO_ROOT = Path(__file__).resolve().parents[2]


def _apply_pca_512(features: np.ndarray) -> np.ndarray:
    """
    Applique une réduction PCA à 512 dimensions.
    Utilise une SVD truncatée pour la réduction dimensionnelle.
    
    Args:
        features: Array [num_frames, feature_dim] (usuellement 2048)
    
    Returns:
        Array [num_frames, 512] avec features réduites
    """
    try:
        from sklearn.decomposition import PCA
        pca = PCA(n_components=512, random_state=42)
        return pca.fit_transform(features).astype(np.float32)
    except ImportError:
        # Si sklearn n'est pas dispo, utiliser une SVD manuelle simple
        # Centrer les données
        mean = np.mean(features, axis=0, keepdims=True)
        centered = features - mean
        
        # SVD
        U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        
        # Prendre les 512 premières composantes
        n_components = min(512, U.shape[1])
        U_reduced = U[:, :n_components]
        
        return (U_reduced * S[:n_components]).astype(np.float32)


def video_to_frames(video_path: str, fps: float = 2.0) -> tuple[int, list[np.ndarray]]:
    """
    Extrait les frames d'une vidéo à une fréquence donnée avec OpenCV.
    
    Args:
        video_path: Chemin vers la vidéo
        fps: Frames par seconde à extraire
    
    Returns:
        Tuple (nb_frames, liste des images numpy)
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Vidéo non trouvée: {video_path}")
    
    # Ouvrir la vidéo avec OpenCV
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Impossible d'ouvrir la vidéo: {video_path}")
    
    # Récupérer les info de la vidéo
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if video_fps <= 0:
        video_fps = 25  # Défaut
    
    # Calculer l'intervalle entre les frames à extraire
    frame_interval = int(video_fps / fps)
    if frame_interval < 1:
        frame_interval = 1
    
    extracted_frames = []
    frame_id = 0
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Extraire tous les N frames
            if frame_id % frame_interval == 0:
                extracted_frames.append(frame)
            
            frame_id += 1
    finally:
        cap.release()
    
    if not extracted_frames:
        raise RuntimeError("Aucune frame extraite de la vidéo")
    
    return len(extracted_frames), extracted_frames



def extract_resnet_features(
    video_path: str,
    output_npy_path: str,
    fps: float = 2.0,
    model_name: str = "resnet50",
    device: str = "auto",
) -> dict:
    """
    Extrait les features ResNET d'une vidéo et les sauvegarde en .npy.
    
    Args:
        video_path: Chemin vers la vidéo
        output_npy_path: Chemin de sortie pour les features (.npy)
        fps: Frames par seconde à analyser
        model_name: Modèle ResNET à utiliser (resnet50, resnet101, etc.)
        device: Appareil pour le calcul ('cpu', 'cuda', 'auto')
    
    Returns:
        Dict avec les statistiques d'extraction
    """
    try:
        import torch
        import torchvision
        from torchvision import transforms, models
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(f"Dépendances PyTorch/torchvision manquantes: {e}")
    
    video_path = Path(video_path)
    output_npy_path = Path(output_npy_path)
    output_npy_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not video_path.exists():
        raise FileNotFoundError(f"Vidéo non trouvée: {video_path}")
    
    # Configurer le device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Charger le modèle ResNET
    if model_name == "resnet50":
        model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    elif model_name == "resnet101":
        model = models.resnet101(weights=models.ResNet101_Weights.IMAGENET1K_V2)
    else:
        raise ValueError(f"Modèle non supporté: {model_name}")
    
    # Supprimer la couche de classification et garder les features
    model = torch.nn.Sequential(*list(model.children())[:-1])
    model.eval()
    model.to(device)
    
    # Préparer les transformations
    preprocess = transforms.Compose([
        transforms.Resize(256),
        transforms.CenterCrop(224),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        ),
    ])
    
    # Extraire les frames
    num_frames, frame_arrays = video_to_frames(str(video_path), fps=fps)
    
    # Extraire les features pour chaque frame
    features_list = []
    
    with torch.no_grad():
        for i, frame_array in enumerate(frame_arrays):
            try:
                # Convertir BGR (OpenCV) à RGB (PIL)
                frame_rgb = cv2.cvtColor(frame_array, cv2.COLOR_BGR2RGB)
                # Convertir numpy array à PIL Image
                image = Image.fromarray(frame_rgb)
                image = preprocess(image)
                image = image.unsqueeze(0).to(device)
                
                features = model(image)
                features = features.squeeze().cpu().numpy()
                features_list.append(features)
            except Exception as e:
                print(f"Erreur traitement frame {i}: {e}")
                continue
    
    if not features_list:
        raise RuntimeError("Aucune feature extraite")
    
    # Empiler les features
    features_array = np.stack(features_list, axis=0)  # Shape: (num_frames, feature_dim)
    
    # Appliquer PCA pour réduire à 512 dimensions si besoin
    if features_array.shape[1] > 512:
        features_array = _apply_pca_512(features_array)
    
    # Sauvegarder les features
    np.save(output_npy_path, features_array)
    
    return {
        "output_path": str(output_npy_path),
        "num_frames": num_frames,
        "feature_shape": tuple(features_array.shape),
        "feature_dim": features_array.shape[1],
        "fps": fps,
    }


def extract_features_from_match_videos(
    match_dir: str,
    fps: float = 2.0,
    device: str = "auto",
) -> dict:
    """
    Extrait les features pour les deux mi-temps d'un match uploadé.
    
    Args:
        match_dir: Dossier contenant 1.mp4 et 2.mp4
        fps: Frames par seconde
        device: Appareil pour le calcul
    
    Returns:
        Dict avec les chemins des features extraites et les statistiques
    """
    match_dir = Path(match_dir)
    
    if not match_dir.exists():
        raise FileNotFoundError(f"Dossier match non trouvé: {match_dir}")
    
    results = {
        "match_dir": str(match_dir),
        "halves": {}
    }
    
    # Trouver et traiter les vidéos
    for half in (1, 2):
        video_patterns = [
            f"{half}.mp4",
            f"{half}.mkv",
            f"{half}.webm",
            f"{half}.mov",
            f"{half}.avi",
        ]
        
        video_path = None
        for pattern in video_patterns:
            candidate = match_dir / pattern
            if candidate.exists():
                video_path = candidate
                break
        
        if video_path is None:
            results["halves"][half] = {
                "status": "error",
                "message": f"Aucune vidéo trouvée pour la mi-temps {half}"
            }
            continue
        
        try:
            output_npy = match_dir / f"{half}_ResNET_TF2_PCA512.npy"
            
            # Extraire les features
            feature_info = extract_resnet_features(
                str(video_path),
                str(output_npy),
                fps=fps,
                device=device
            )
            
            results["halves"][half] = {
                "status": "success",
                "video_path": str(video_path),
                "features_path": str(output_npy),
                "num_frames": feature_info["num_frames"],
                "feature_shape": feature_info["feature_shape"],
            }
        
        except Exception as e:
            results["halves"][half] = {
                "status": "error",
                "message": str(e),
                "video_path": str(video_path),
            }
    
    return results
