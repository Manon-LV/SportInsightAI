#!/usr/bin/env python3
"""
Script pour importer et analyser des vidéos personnalisées via l'API SportInsight.

Usage:
    python apps/api/upload_example.py --match-name "My Match" --video-1 path/to/half1.mp4 --video-2 path/to/half2.mp4 --checkpoint path/to/best.pt

Ou utiliser de manière interactive:
    python apps/api/upload_example.py
"""

import argparse
import time
import requests
import json
from pathlib import Path
from typing import Optional


class SportInsightUploadClient:
    """Client pour uploader et analyser des vidéos."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    def create_job(self, match_name: str) -> str:
        """Crée un nouveau job d'upload."""
        response = requests.post(
            f"{self.base_url}/upload/create",
            data={"match_name": match_name}
        )
        response.raise_for_status()
        data = response.json()
        return data["job_id"]
    
    def upload_video(self, job_id: str, half: int, video_path: str) -> dict:
        """Upload une vidéo pour une mi-temps."""
        with open(video_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/upload/{job_id}/video/{half}",
                files={"file": f}
            )
        response.raise_for_status()
        return response.json()
    
    def finalize_upload(self, job_id: str) -> dict:
        """Finalise l'upload."""
        response = requests.post(f"{self.base_url}/upload/{job_id}/finalize")
        response.raise_for_status()
        return response.json()
    
    def extract_features(self, job_id: str, fps: float = 2.0, device: str = "auto") -> dict:
        """Extrait les features des vidéos."""
        response = requests.post(
            f"{self.base_url}/upload/{job_id}/extract-features",
            params={"fps": fps, "device": device}
        )
        response.raise_for_status()
        return response.json()
    
    def get_status(self, job_id: str) -> dict:
        """Récupère l'état du job."""
        response = requests.get(f"{self.base_url}/upload/{job_id}")
        response.raise_for_status()
        return response.json()
    
    def run_inference(self, match_dir: str, checkpoint: str, half: str = "both") -> dict:
        """Lance l'inférence sur le match uploadé."""
        response = requests.post(
            f"{self.base_url}/inference/run",
            json={
                "match_dir": match_dir,
                "checkpoint": checkpoint,
                "half": half,
                "score_threshold": 0.30,
                "nms_radius_sec": 6.0,
            }
        )
        response.raise_for_status()
        return response.json()
    
    def upload_and_analyze(
        self,
        match_name: str,
        video_1_path: str,
        video_2_path: str,
        checkpoint: str,
        half: str = "both",
        fps: float = 2.0,
        device: str = "auto",
    ) -> dict:
        """Workflow complet: upload -> extract features -> inférence."""
        
        print(f"\n{'='*60}")
        print(f"📺 Analyse: {match_name}")
        print(f"{'='*60}\n")
        
        # 1. Créer le job
        print("1️⃣ Création du job d'upload...")
        job_id = self.create_job(match_name)
        print(f"   ✓ Job créé: {job_id}\n")
        
        # 2. Upload mi-temps 1
        print("2️⃣ Upload de la mi-temps 1...")
        result = self.upload_video(job_id, 1, video_1_path)
        print(f"   ✓ Uploadée: {result['size'] / 1024 / 1024:.1f} MB\n")
        
        # 3. Upload mi-temps 2
        print("3️⃣ Upload de la mi-temps 2...")
        result = self.upload_video(job_id, 2, video_2_path)
        print(f"   ✓ Uploadée: {result['size'] / 1024 / 1024:.1f} MB\n")
        
        # 4. Finaliser l'upload
        print("4️⃣ Finalisation de l'upload...")
        status = self.finalize_upload(job_id)
        match_dir = status["match_dir"]
        print(f"   ✓ Match directory: {match_dir}\n")
        
        # 5. Extraire les features
        print("5️⃣ Extraction des features ResNET (peut prendre quelques minutes)...")
        features = self.extract_features(job_id, fps=fps, device=device)
        print(f"   ✓ Features extraites\n")
        print(f"   Halves info:")
        for h, info in features["halves"].items():
            if info.get("status") == "success":
                print(f"     - Half {h}: {info['num_frames']} frames, shape {info['feature_shape']}")
            else:
                print(f"     - Half {h}: {info.get('message', 'Unknown error')}")
        print()
        
        # 6. Lancer l'inférence
        print("6️⃣ Lancement de l'inférence...")
        inference = self.run_inference(match_dir, checkpoint, half=half)
        events = inference["events"]
        summary = inference["summary"]
        
        print(f"   ✓ Analyse terminée!\n")
        print(f"   📊 Résumé:")
        print(f"     - Événements détectés: {summary['event_count']}")
        print(f"     - Par classe: {json.dumps(summary['counts_by_class'], indent=8)}")
        print(f"     - Par mi-temps: {summary['counts_by_half']}\n")
        
        # 7. Afficher les événements
        print(f"   🎬 Événements:")
        for i, event in enumerate(events[:10], 1):
            print(f"     {i}. {event['label']} @ {event['gameTime']} (score: {event['score']:.2f})")
        if len(events) > 10:
            print(f"     ... et {len(events) - 10} autres")
        print()
        
        return inference


def main():
    parser = argparse.ArgumentParser(
        description="Import et analyse de vidéos personnalisées via SportInsight API"
    )
    parser.add_argument("--base-url", default="http://localhost:8000", help="URL de l'API")
    parser.add_argument("--match-name", required=True, help="Nom du match")
    parser.add_argument("--video-1", required=True, help="Chemin vers la vidéo mi-temps 1")
    parser.add_argument("--video-2", required=True, help="Chemin vers la vidéo mi-temps 2")
    parser.add_argument("--checkpoint", required=True, help="Chemin vers le checkpoint du modèle")
    parser.add_argument("--half", default="both", choices=["first", "second", "both"], help="Mi-temps à analyser")
    parser.add_argument("--fps", type=float, default=2.0, help="Frames par seconde pour l'extraction")
    parser.add_argument("--device", default="auto", help="Device pour le calcul (auto, cpu, cuda)")
    
    args = parser.parse_args()
    
    # Vérifier que les fichiers existent
    for path in [args.video_1, args.video_2, args.checkpoint]:
        if not Path(path).exists():
            print(f"❌ Fichier non trouvé: {path}")
            return 1
    
    # Créer le client et lancer le workflow
    client = SportInsightUploadClient(args.base_url)
    
    try:
        result = client.upload_and_analyze(
            match_name=args.match_name,
            video_1_path=args.video_1,
            video_2_path=args.video_2,
            checkpoint=args.checkpoint,
            half=args.half,
            fps=args.fps,
            device=args.device,
        )
        print("✅ Analyse complète et réussie!")
        return 0
    
    except requests.exceptions.ConnectionError:
        print("❌ Impossible de se connecter à l'API")
        print(f"   Vérifiez que l'API est démarrée: {args.base_url}")
        print("   Commande: uvicorn apps.api.main:app --reload")
        return 1
    
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
