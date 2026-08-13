import os
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance

def compute_ela_score(image_path: str, scale: int = 15, quality: int = 90) -> tuple[float, bool, str]:
    """
    Fast Error Level Analysis (ELA) with image resizing & disk caching.
    Returns:
      - ela_score (float [0.0 - 1.0])
      - tamper_detected (bool)
      - ela_image_path (str)
    """
    if not os.path.exists(image_path):
        return 0.0, False, ""
    
    ela_map_path = image_path + "_ela.jpg"
    
    try:
        orig = Image.open(image_path).convert('RGB')
        
        # Performance optimization: Resize large high-res documents for fast array processing
        if orig.width > 1200 or orig.height > 1200:
            orig.thumbnail((1200, 1200), Image.Resampling.BILINEAR)

        # Temporary recompressed file
        temp_filename = image_path + ".temp_ela.jpg"
        orig.save(temp_filename, 'JPEG', quality=quality)
        
        recompressed = Image.open(temp_filename).convert('RGB')
        diff = ImageChops.difference(orig, recompressed)
        
        extrema = diff.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        if max_diff == 0:
            max_diff = 1
            
        scale_factor = 255.0 / max_diff
        diff_enhanced = ImageEnhance.Brightness(diff).enhance(scale_factor * (scale / 10.0))
        diff_enhanced.save(ela_map_path)
        
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        ela_np = np.array(diff_enhanced)
        gray = cv2.cvtColor(ela_np, cv2.COLOR_RGB2GRAY)
        
        std_dev = float(np.std(gray))
        mean_val = float(np.mean(gray))
        
        score = min(1.0, round((std_dev * 1.5 + mean_val * 0.5) / 100.0, 3))
        tamper_detected = score > 0.45
        
        return score, tamper_detected, ela_map_path
    except Exception as e:
        print(f"Error computing ELA for {image_path}: {e}")
        return 0.0, False, ""
