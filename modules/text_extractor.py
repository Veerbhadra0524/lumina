import os
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from config import Config

logger = logging.getLogger(__name__)

class TextExtractor:
    """Optimized OCR with selective semantic chunking"""
    
    def __init__(self):
        self.config = Config()
        # Phase 2 Fix: Only load chunking model when needed
        self.chunking_model = None
        self.chunking_enabled = False  # Start disabled
    
    def _lazy_load_chunking_model(self):
        """Only load chunking model when explicitly needed"""
        if self.chunking_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self.chunking_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info(f"SUCCESS: Chunking model loaded on demand")
            except Exception as e:
                logger.warning(f"Chunking model loading failed: {str(e)}")
                self.chunking_model = False  # Mark as failed
    
    def extract_text(self, upload_id: str, enable_chunking: bool = False) -> Dict[str, Any]:
        """Extract text with optional semantic chunking"""
        try:
            upload_dir = os.path.join(self.config.UPLOAD_FOLDER, upload_id)
            metadata_path = os.path.join(upload_dir, 'metadata.json')
            
            if not os.path.exists(metadata_path):
                return {'success': False, 'error': 'Document metadata not found'}
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"PROCESSING: Processing text extraction for upload {upload_id}")
            
            text_blocks = []
            pages = metadata.get('pages', [])
            
            if not pages:
                return {'success': False, 'error': 'No pages found in metadata'}
            
            for i, page in enumerate(pages):
                # Handle different possible path keys
                image_path = None
                for path_key in ['path', 'image_path', 'file_path']:
                    if path_key in page:
                        image_path = page[path_key]
                        break
                
                if not image_path:
                    logger.warning(f"WARNING: No path found in page {i}, skipping")
                    continue
                
                page_number = page.get('page_number', page.get('slide_number', i))
                
                if not os.path.exists(image_path):
                    logger.warning(f"WARNING: Image file not found: {image_path}")
                    continue
                
                logger.info(f"EXTRACTING: Extracting text from page {page_number}: {image_path}")
                
                # Phase 2 Fix: Use optimized OCR
                page_result = self._extract_text_with_optimized_ocr(image_path, page_number)
                
                if page_result['success']:
                    extracted_blocks = page_result['text_blocks']
                    text_blocks.extend(extracted_blocks)
                    logger.info(f"SUCCESS: Extracted {len(extracted_blocks)} text blocks from page {page_number}")
                else:
                    logger.warning(f"WARNING: OCR failed for page {page_number}: {page_result.get('error', 'Unknown error')}")
            
            # Phase 2 Fix: Only apply chunking if explicitly enabled AND beneficial
            original_count = len(text_blocks)
            if enable_chunking and original_count > 10:  # Only chunk if many blocks
                self._lazy_load_chunking_model()
                if self.chunking_model:
                    text_blocks = self._apply_conservative_chunking(text_blocks, upload_id)
                    logger.info(f"🧠 Conservative chunking: {original_count} → {len(text_blocks)} chunks")
            
            # Save extracted text
            text_result = {
                'upload_id': upload_id,
                'extracted_at': str(datetime.now()),
                'total_blocks': len(text_blocks),
                'text_blocks': text_blocks,
                'original_blocks': original_count,
                'chunking_applied': len(text_blocks) != original_count
            }
            
            result_path = os.path.join(upload_dir, 'extracted_text.json')
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(text_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"COMPLETED: Text extraction completed: {len(text_blocks)} total blocks extracted")
            
            return {
                'success': True,
                'text_blocks': text_blocks,
                'total_blocks': len(text_blocks)
            }
            
        except Exception as e:
            logger.error(f"Text extraction error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _extract_text_with_optimized_ocr(self, image_path: str, page_number: int) -> Dict[str, Any]:
        """Phase 2 Fix: Optimized OCR focused on accuracy"""
        try:
            logger.debug(f"Loading image: {image_path}")
            
            original_image = cv2.imread(image_path)
            if original_image is None:
                try:
                    pil_img = Image.open(image_path)
                    original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    return {'success': False, 'error': f'Could not load image: {str(e)}'}
            
            # Phase 2 Fix: Focus on 3 best preprocessing methods only
            preprocessed_images = self._create_focused_preprocessed_versions(original_image)
            
            all_results = []
            
            # Extract text from each preprocessed version
            for prep_name, prep_image in preprocessed_images.items():
                try:
                    pil_image = Image.fromarray(cv2.cvtColor(prep_image, cv2.COLOR_BGR2RGB))
                    
                    # Phase 2 Fix: Use only the best OCR config
                    config = r'--oem 3 --psm 6'  # Most reliable config
                    
                    try:
                        data = pytesseract.image_to_data(
                            pil_image,
                            config=config,
                            output_type=pytesseract.Output.DICT
                        )
                        
                        # Phase 2 Fix: Preserve original confidence scores
                        page_text = self._extract_confident_text_preserve_quality(data, prep_name, config)
                        all_results.extend(page_text)
                        
                    except Exception as e:
                        logger.debug(f"OCR config {config} failed for {prep_name}: {e}")
                        continue
                    
                except Exception as e:
                    logger.debug(f"Preprocessing {prep_name} failed: {e}")
                    continue
            
            # Phase 2 Fix: Conservative deduplication
            final_blocks = self._conservative_merge_and_deduplicate(all_results, page_number)
            
            logger.info(f"Optimized OCR extracted {len(final_blocks)} blocks from page {page_number}")
            
            return {
                'success': True,
                'text_blocks': final_blocks,
                'methods_used': list(preprocessed_images.keys())
            }
            
        except Exception as e:
            logger.error(f"Optimized OCR error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _create_focused_preprocessed_versions(self, image):
        """FIXED: Enhanced preprocessing with proper OCR optimizer integration"""
        try:
            # Try OCR optimizer first
            try:
                from modules.ocr_optimizer import OCROptimizer
                # FIXED: Pass the actual image, not None
                enhanced_versions = OCROptimizer.enhance_image_for_ocr_direct(image)
                if enhanced_versions and len(enhanced_versions) > 1:
                    logger.info(f"SUCCESS: Using OCR optimizer enhanced versions")
                    return enhanced_versions
            except (ImportError, Exception) as e:
                logger.debug(f"OCR optimizer not available: {e}")
            
            # Fallback to enhanced method
            versions = {}
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Method 1: Enhanced contrast - IMPROVED
            clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            versions['enhanced_contrast'] = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            # Method 2: Denoised version - IMPROVED
            denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
            versions['denoised'] = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
            
            # Method 3: Adaptive threshold - OPTIMIZED
            adaptive_thresh = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 13, 3
            )
            versions['adaptive_thresh'] = cv2.cvtColor(adaptive_thresh, cv2.COLOR_GRAY2BGR)
            
            return versions
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return {'original': image}
    
    def _extract_confident_text_preserve_quality(self, ocr_data, method_name, config_name):
        """FIXED: Single confidence boost logic"""
        text_blocks = []
        
        try:
            current_text = ""
            current_confidences = []
            current_boxes = []
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                # Phase 2 Fix: Lower threshold but preserve high confidence
                if text and confidence > 30:  # Lower threshold
                    current_text += text + " "
                    current_confidences.append(confidence)
                    current_boxes.append([
                        ocr_data['left'][i],
                        ocr_data['top'][i],
                        ocr_data['width'][i],
                        ocr_data['height'][i]
                    ])
                    
                    if len(current_text.split()) >= 3:
                        cleaned_text = self._clean_and_validate_text(current_text.strip())
                        
                        if cleaned_text and len(cleaned_text) >= self.config.MIN_TEXT_LENGTH:
                            # Phase 2 Fix: Preserve original confidence without dilution
                            raw_confidence = sum(current_confidences) / len(current_confidences)
                            
                            # FIXED: Single confidence calculation with boosting
                            final_confidence = min(0.95, raw_confidence / 100.0)
                            
                            # ENHANCED CONFIDENCE BOOSTING (Replaces old logic)
                            if raw_confidence > 85:  # High quality text
                                final_confidence = min(0.95, final_confidence * 1.3)  # 30% boost
                            elif raw_confidence > 70:  # Good quality text
                                final_confidence = min(0.90, final_confidence * 1.2)  # 20% boost
                            elif raw_confidence > 50:  # Moderate quality
                                final_confidence = min(0.85, final_confidence * 1.1)  # 10% boost
                            
                            text_blocks.append({
                                'text': cleaned_text,
                                'confidence': final_confidence,
                                'raw_confidence': raw_confidence,  # Keep raw score
                                'bbox': self._merge_bounding_boxes(current_boxes),
                                'method': f"{method_name}_{config_name}",
                                'word_count': len(cleaned_text.split()),
                                'char_count': len(cleaned_text)
                            })
                        
                        current_text = ""
                        current_confidences = []
                        current_boxes = []
            
            # Handle remaining text
            if current_text.strip():
                cleaned_text = self._clean_and_validate_text(current_text.strip())
                if cleaned_text and len(cleaned_text) >= self.config.MIN_TEXT_LENGTH:
                    raw_confidence = sum(current_confidences) / len(current_confidences) if current_confidences else 60
                    final_confidence = min(0.95, raw_confidence / 100.0)
                    
                    # Apply same boosting logic
                    if raw_confidence > 85:
                        final_confidence = min(0.95, final_confidence * 1.3)
                    elif raw_confidence > 70:
                        final_confidence = min(0.90, final_confidence * 1.2)
                    elif raw_confidence > 50:
                        final_confidence = min(0.85, final_confidence * 1.1)
                    
                    text_blocks.append({
                        'text': cleaned_text,
                        'confidence': final_confidence,
                        'raw_confidence': raw_confidence,
                        'bbox': self._merge_bounding_boxes(current_boxes) if current_boxes else [0, 0, 100, 100],
                        'method': f"{method_name}_{config_name}",
                        'word_count': len(cleaned_text.split()),
                        'char_count': len(cleaned_text)
                    })
            
            return text_blocks
            
        except Exception as e:
            logger.error(f"Confident text extraction failed: {e}")
            return []
    
    def _conservative_merge_and_deduplicate(self, all_results, page_number):
        """Phase 2 Fix: Conservative deduplication to preserve quality"""
        if not all_results:
            return []
        
        # Sort by raw confidence (not processed confidence)
        all_results.sort(key=lambda x: x.get('raw_confidence', x.get('confidence', 0) * 100), reverse=True)
        
        final_blocks = []
        used_texts = set()
        
        for block in all_results:
            text = block['text'].lower().strip()
            
            # Phase 2 Fix: More lenient deduplication (0.9 instead of 0.8)
            is_duplicate = False
            for used_text in used_texts:
                if self._text_similarity(text, used_text) > 0.9:  # Higher threshold
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                block['page_number'] = page_number
                final_blocks.append(block)
                used_texts.add(text)
        
        # Phase 2 Fix: Keep more blocks (30 instead of 20)
        return final_blocks[:30]
    
    def _apply_conservative_chunking(self, text_blocks: List[Dict[str, Any]], upload_id: str) -> List[Dict[str, Any]]:
        """Phase 2 Fix: Conservative chunking - only when beneficial"""
        try:
            if len(text_blocks) < 8:  # Don't chunk small documents
                return text_blocks
            
            logger.info(f"🧠 Applying conservative chunking to {len(text_blocks)} text blocks")
            
            # Group blocks by page
            pages = {}
            for block in text_blocks:
                page_num = block.get('page_number', 0)
                if page_num not in pages:
                    pages[page_num] = []
                pages[page_num].append(block)
            
            chunked_blocks = []
            
            # Process each page
            for page_num, page_blocks in pages.items():
                if len(page_blocks) <= 4:  # Don't chunk small pages
                    chunked_blocks.extend(page_blocks)
                    continue
                
                # Only chunk if it reduces blocks significantly
                page_chunks = self._create_conservative_chunks(page_blocks, page_num, upload_id)
                
                # Phase 2 Fix: Only use chunks if they reduce count by less than 50%
                reduction_ratio = len(page_chunks) / len(page_blocks)
                if reduction_ratio > 0.5:  # Keep chunks only if reasonable reduction
                    chunked_blocks.extend(page_chunks)
                else:
                    chunked_blocks.extend(page_blocks)  # Keep originals
            
            return chunked_blocks
            
        except Exception as e:
            logger.error(f"Conservative chunking error: {str(e)}")
            return text_blocks
    
    def _create_conservative_chunks(self, blocks: List[Dict[str, Any]], page_num: int, upload_id: str) -> List[Dict[str, Any]]:
        """Create chunks only when semantically beneficial"""
        try:
            if len(blocks) <= 2:
                return blocks
            
            chunks = []
            current_chunk_text = ""
            current_chunk_blocks = []
            
            for block in blocks:
                block_text = block['text']
                
                # Conservative chunking: only chunk if very similar (0.6+ similarity)
                if current_chunk_text and len(current_chunk_text) > 30:
                    similarity = self._calculate_semantic_similarity(current_chunk_text, block_text)
                    
                    # Phase 2 Fix: Higher similarity threshold (0.6 instead of 0.4)
                    if similarity < 0.6 or len(current_chunk_text) > 500:
                        # Finalize current chunk
                        if current_chunk_text.strip():
                            chunk = self._create_chunk(
                                current_chunk_text, 
                                current_chunk_blocks, 
                                page_num, 
                                upload_id, 
                                len(chunks)
                            )
                            chunks.append(chunk)
                        
                        # Start new chunk
                        current_chunk_text = block_text
                        current_chunk_blocks = [block]
                    else:
                        # Add to current chunk
                        current_chunk_text += " " + block_text
                        current_chunk_blocks.append(block)
                else:
                    if current_chunk_text:
                        current_chunk_text += " " + block_text
                    else:
                        current_chunk_text = block_text
                    current_chunk_blocks.append(block)
            
            # Add final chunk
            if current_chunk_text.strip():
                chunk = self._create_chunk(
                    current_chunk_text, 
                    current_chunk_blocks, 
                    page_num, 
                    upload_id, 
                    len(chunks)
                )
                chunks.append(chunk)
            
            return chunks if chunks else blocks
            
        except Exception as e:
            logger.error(f"Conservative chunk creation error: {str(e)}")
            return blocks
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity with fallback"""
        try:
            if self.chunking_model and self.chunking_model is not False:
                embeddings = self.chunking_model.encode([text1, text2])
                similarity = np.dot(embeddings[0], embeddings[1]) / (
                    np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
                )
                return float(similarity)
            else:
                return self._calculate_word_overlap(text1, text2)
                
        except Exception as e:
            return self._calculate_word_overlap(text1, text2)
    
    def _calculate_word_overlap(self, text1: str, text2: str) -> float:
        """Fallback word overlap calculation"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
    
    # Keep all existing helper methods unchanged
    def _clean_and_validate_text(self, text: str) -> str:
        """Enhanced text cleaning and validation"""
        if not text:
            return ""
        
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common OCR errors
        fixes = {
            r'\b1(?=\s|[A-Z]|$)': 'I',
            r'\b0(?=\s|[A-Z]|$)': 'O',
            r'([a-z])\s+([a-z])(?=\s|$)': r'\1\2',
            r'(\w)\s+(\.)': r'\1\2',
        }
        
        for pattern, replacement in fixes.items():
            text = re.sub(pattern, replacement, text)
        
        words = text.split()
        words = [word for word in words if len(word) > 1 or word.isdigit() or word.isalpha()]
        
        text = ' '.join(words).strip()
        
        if len(text) < 3:
            return ""
        
        # Check character distribution
        alpha_count = sum(c.isalpha() for c in text)
        total_chars = len(text.replace(' ', ''))
        
        if total_chars > 0 and alpha_count / total_chars < 0.3:
            return ""
        
        return text
    
    def _merge_bounding_boxes(self, boxes):
        """Merge multiple bounding boxes into one"""
        if not boxes:
            return [0, 0, 0, 0]
        
        min_x = min(box[0] for box in boxes)
        min_y = min(box[1] for box in boxes)
        max_x = max(box[0] + box[2] for box in boxes)
        max_y = max(box[1] + box[3] for box in boxes)
        
        return [min_x, min_y, max_x - min_x, max_y - min_y]
    
    def _create_chunk(self, text: str, metadata_blocks: List[Dict], page_num: int, upload_id: str, chunk_id: int) -> Dict[str, Any]:
        """Create a chunk with preserved confidence"""
        # Phase 2 Fix: Preserve highest confidence instead of averaging
        confidences = [block.get('confidence', 0.5) for block in metadata_blocks]
        max_confidence = max(confidences) if confidences else 0.5
        
        # Use max confidence instead of average to preserve quality
        final_confidence = max_confidence
        
        # Merge bounding boxes
        bboxes = [block.get('bbox', [0, 0, 0, 0]) for block in metadata_blocks if 'bbox' in block]
        merged_bbox = self._merge_bounding_boxes(bboxes) if bboxes else [0, 0, 0, 0]
        
        return {
            'text': text.strip(),
            'page_number': page_num,
            'confidence': final_confidence,  # Preserved confidence
            'bbox': merged_bbox,
            'upload_id': upload_id,
            'chunk_id': chunk_id,
            'chunk_type': 'conservative_semantic',
            'source_blocks': len(metadata_blocks),
            'method': 'conservative_chunking'
        }
    
    def _text_similarity(self, text1, text2):
        """Calculate similarity between two texts"""
        if not text1 or not text2:
            return 0.0
        
        words1 = set(text1.split())
        words2 = set(text2.split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
