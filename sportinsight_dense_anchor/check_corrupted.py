import numpy as np
from pathlib import Path

data_dir = Path('data/SoccerNet')
corrupted = []

print("Vérification des fichiers .npy...")
for i, npy_file in enumerate(sorted(data_dir.glob('**/*_ResNET_TF2_PCA512.npy'))):
    try:
        arr = np.load(npy_file, allow_pickle=False)
        if i % 20 == 0:
            print(f"  [{i:3d}] OK: {npy_file.parent.name}")
    except (ValueError, OSError) as e:
        corrupted.append((npy_file, str(e)))
        print(f"  ❌ CORROMPU: {npy_file}")
        print(f"     Erreur: {str(e)[:100]}")

print(f"\nRésumé: {len(corrupted)} fichier(s) corrompu(s)")
if corrupted:
    print("\nFichiers à supprimer/régénérer:")
    for path, err in corrupted:
        print(f"  - {path}")
