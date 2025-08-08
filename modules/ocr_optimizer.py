import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import logging

logger = logging.getLogger(__name__)

class OCROptimizer:
    """Final OCR optimization for maximum accuracy"""
    
    @staticmethod
    def enhance_image_for_ocr_direct(image: np.ndarray) -> dict:
        """Apply optimizations directly to image array"""
        try:
            if image is None:
                logger.error("Image is None in OCR optimizer")
                return {}
            
            # Apply targeted enhancements
            enhanced_versions = {}
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image.copy()
            
            # Version 1: Ultra-sharp enhancement
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
            
            logger.info(f"SUCCESS: OCR Optimizer created {len(enhanced_versions)} enhanced versions")
            return enhanced_versions
            
        except Exception as e:
            logger.error(f"Image enhancement failed: {e}")
            return {}
