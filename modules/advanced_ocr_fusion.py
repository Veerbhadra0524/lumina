import logging
from typing import Dict, List, Any, Optional
import pytesseract
import easyocr
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import torch
import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class MultiEngineOCR:
    """Advanced OCR system combining multiple engines for maximum accuracy"""
    
    def __init__(self):
        self.engines = {}
        self._initialize_ocr_engines()
    
    def _initialize_ocr_engines(self):
        """Initialize multiple OCR engines"""
        # Tesseract (reliable for clean text)
        try:
            self.engines['tesseract'] = {
                'available': True,
                'confidence_weight': 0.3,
                'best_for': ['clean_text', 'structured_docs']
            }
            logger.info("✅ Tesseract OCR initialized")
        except Exception as e:
            logger.warning(f"Tesseract failed: {e}")
        
        # EasyOCR (good for various fonts/languages)
        try:
            self.easyocr_reader = easyocr.Reader(['en'], gpu=torch.cuda.is_available())
            self.engines['easyocr'] = {
                'available': True,
                'confidence_weight': 0.35,
                'best_for': ['handwriting', 'varied_fonts']
            }
            logger.info("✅ EasyOCR initialized")
        except Exception as e:
            logger.warning(f"EasyOCR failed: {e}")
        
        # TrOCR (state-of-the-art transformer-based OCR)
        try:
            self.trocr_processor = TrOCRProcessor.from_pretrained('microsoft/trocr-large-printed')
            self.trocr_model = VisionEncoderDecoderModel.from_pretrained('microsoft/trocr-large-printed')
            if torch.cuda.is_available():
                self.trocr_model = self.trocr_model.to('cuda')
            self.engines['trocr'] = {
                'available': True,
                'confidence_weight': 0.35,
                'best_for': ['printed_text', 'high_quality']
            }
            logger.info("✅ TrOCR initialized")
        except Exception as e:
            logger.warning(f"TrOCR failed: {e}")
    
    def extract_with_fusion(self, image_path: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract text using all available OCR engines and fuse results"""
        results = []
        
        # Extract with each engine
        if self.engines.get('tesseract', {}).get('available'):
            tesseract_result = self._extract_tesseract(image_path, page_number)
            results.extend(tesseract_result)
        
        if self.engines.get('easyocr', {}).get('available'):
            easyocr_result = self._extract_easyocr(image_path, page_number)
            results.extend(easyocr_result)
        
        if self.engines.get('trocr', {}).get('available'):
            trocr_result = self._extract_trocr(image_path, page_number)
            results.extend(trocr_result)
        
        # Intelligent fusion
        fused_results = self._intelligent_fusion(results)
        
        logger.info(f"📊 OCR Fusion: {len(results)} raw → {len(fused_results)} fused results")
        return fused_results
    
    def _extract_tesseract(self, image_path: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract using Tesseract with multiple configurations"""
        try:
            img = cv2.imread(image_path)
            results = []
            
            configs = [
                '--oem 3 --psm 6',  # Uniform block
                '--oem 3 --psm 4',  # Single column
                '--oem 3 --psm 3'   # Fully automatic
            ]
            
            for config in configs:
                try:
                    data = pytesseract.image_to_data(
                        img, config=config, output_type=pytesseract.Output.DICT
                    )
                    
                    current_text = ""
                    confidences = []
                    
                    for i in range(len(data['text'])):
                        text = data['text'][i].strip()
                        conf = int(data['conf'][i])
                        
                        if text and conf > 30:
                            current_text += text + " "
                            confidences.append(conf)
                            
                            if len(current_text.split()) >= 5:
                                avg_conf = sum(confidences) / len(confidences) / 100.0
                                results.append({
                                    'text': current_text.strip(),
                                    'confidence': avg_conf,
                                    'page_number': page_number,
                                    'engine': 'tesseract',
                                    'config': config,
                                    'bbox': [data['left'][i], data['top'][i], 
                                            data['width'][i], data['height'][i]]
                                })
                                current_text = ""
                                confidences = []
                except Exception as e:
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Tesseract extraction failed: {e}")
            return []
    
    def _extract_easyocr(self, image_path: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract using EasyOCR"""
        try:
            results = self.easyocr_reader.readtext(image_path)
            text_blocks = []
            
            for i, (bbox, text, conf) in enumerate(results):
                if text.strip() and conf > 0.3:
                    # Convert bbox format
                    x_coords = [point[0] for point in bbox]
                    y_coords = [point[1] for point in bbox]
                    x, y = min(x_coords), min(y_coords)
                    w, h = max(x_coords) - x, max(y_coords) - y
                    
                    text_blocks.append({
                        'text': text.strip(),
                        'confidence': conf,
                        'page_number': page_number,
                        'engine': 'easyocr',
                        'bbox': [int(x), int(y), int(w), int(h)]
                    })
            
            return text_blocks
        except Exception as e:
            logger.error(f"EasyOCR extraction failed: {e}")
            return []
    
    def _extract_trocr(self, image_path: str, page_number: int) -> List[Dict[str, Any]]:
        """Extract using TrOCR (transformer-based)"""
        try:
            image = Image.open(image_path).convert('RGB')
            pixel_values = self.trocr_processor(image, return_tensors="pt").pixel_values
            
            if torch.cuda.is_available():
                pixel_values = pixel_values.to('cuda')
            
            generated_ids = self.trocr_model.generate(pixel_values, max_length=512)
            generated_text = self.trocr_processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            if generated_text.strip():
                # Estimate confidence based on text quality
                confidence = self._estimate_trocr_confidence(generated_text, image)
                
                return [{
                    'text': generated_text.strip(),
                    'confidence': confidence,
                    'page_number': page_number,
                    'engine': 'trocr',
                    'bbox': [0, 0, image.width, image.height]
                }]
            
            return []
        except Exception as e:
            logger.error(f"TrOCR extraction failed: {e}")
            return []
    
    def _intelligent_fusion(self, all_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Intelligently fuse results from multiple OCR engines"""
        if not all_results:
            return []
        
        # Group similar texts
        grouped = {}
        for result in all_results:
            text_key = result['text'].lower().strip()[:50]  # First 50 chars for grouping
            
            if text_key not in grouped:
                grouped[text_key] = []
            grouped[text_key].append(result)
        
        # Select best result from each group
        fused_results = []
        for group in grouped.values():
            # Sort by confidence and engine priority
            engine_priority = {'trocr': 3, 'easyocr': 2, 'tesseract': 1}
            
            best_result = max(group, key=lambda x: (
                x['confidence'], 
                engine_priority.get(x['engine'], 0)
            ))
            
            # Boost confidence if multiple engines agree
            if len(group) > 1:
                best_result['confidence'] = min(0.95, best_result['confidence'] * 1.2)
                best_result['consensus_engines'] = len(group)
            
            fused_results.append(best_result)
        
        return fused_results
    
    def _estimate_trocr_confidence(self, text: str, image: Image.Image) -> float:
        """Estimate confidence for TrOCR results"""
        confidence = 0.8  # Base confidence
        
        # Text length bonus
        if len(text) > 50:
            confidence += 0.1
        
        # Check for artifacts
        artifacts = [r'\*+', r'#{3,}', r'[@#$%^&*]{3,}']
        import re
        for pattern in artifacts:
            if re.search(pattern, text):
                confidence -= 0.2
                break
        
        # Word quality check
        words = text.split()
        if words:
            valid_words = sum(1 for word in words if len(word) > 1 and word.isalnum())
            word_ratio = valid_words / len(words)
            confidence *= word_ratio
        
        return max(0.1, min(0.99, confidence))

# Usage in your main text_extractor.py
ocr_fusion = MultiEngineOCR()
