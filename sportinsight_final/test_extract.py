#!/usr/bin/env python3
from apps.api.features_service import extract_resnet_features
import os
import traceback

video_path = 'apps/api/storage/uploads/upload_e1293a26bff9/test2/1.mp4'
output_path = 'apps/api/storage/uploads/upload_e1293a26bff9/test2/1_ResNET_TF2_PCA512.npy'

if os.path.exists(output_path):
    os.remove(output_path)
    print('Ancien fichier supprime')

try:
    print('Extraction des features ResNET50...')
    result = extract_resnet_features(video_path, output_path, fps=2.0, device='auto')
    
    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        print('SUCCESS!')
        print(f'File created: {output_path}')
        print(f'Size: {size / 1024 / 1024:.2f} MB')
        print(f'Shape: {result["feature_shape"]}')
    else:
        print('File not created!')
except Exception as e:
    print(f'ERROR: {e}')
    traceback.print_exc()
