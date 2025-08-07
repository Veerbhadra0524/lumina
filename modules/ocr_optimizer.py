import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import logging

logger = logging.getLogger(__name__)

class OCROptimizer:
    """Final OCR optimization for maximum accuracy"""
    
    @staticmethod
    def enhance_image_for_ocr(image_path: str) -> dict:
        """Apply final optimizations for maximum OCR accuracy"""
        try:
            # Load image
            original = cv2.imread(image_path)
            if original is None:
                pil_img = Image.open(image_path)
                original = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            
            # Apply targeted enhancements
            enhanced_versions = {}
            
            # Version 1: Ultra-sharp enhancement
            gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            
            # Sharpen specifically for text
            kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
            sharpened = cv2.filter2D(gray, -1, kernel)
            
            # Enhanced contrast with optimized CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8,8))
            enhanced = clahe.apply(sharpened)
            
            enhanced_versions['ultra_sharp'] = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            # Version 2: Denoised + Enhanced
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            enhanced_denoised = clahe.apply(denoised)
            enhanced_versions['denoised_enhanced'] = cv2.cvtColor(enhanced_denoised, cv2.COLOR_GRAY2BGR)
            
            # Version 3: Morphological enhancement for text
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,1))
            morph = cv2.morphologyEx(enhanced, cv2.MORPH_CLOSE, kernel)
            enhanced_versions['morphological'] = cv2.cvtColor(morph, cv2.COLOR_GRAY2BGR)
            
            return enhanced_versions
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return {'original': original}
