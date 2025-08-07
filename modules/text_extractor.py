import os
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import cv2
import numpy as np
import logging
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sentence_transformers import SentenceTransformer
from config import Config

logger = logging.getLogger(__name__)

class TextExtractor:
    """Enhanced OCR with semantic chunking and advanced preprocessing"""
    
    def __init__(self):
        self.config = Config()
        # Phase 2: Semantic chunking
        self.chunking_model = None
        self._initialize_chunking_model()
    
    def _initialize_chunking_model(self):
        """Initialize model for semantic chunking"""
        try:
            self.chunking_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Semantic chunking model initialized")
        except Exception as e:
            logger.warning(f"Chunking model initialization failed: {str(e)}")
            self.chunking_model = None
    
    def extract_text(self, upload_id: str) -> Dict[str, Any]:
        """Main extraction method (backward compatible)"""
        try:
            upload_dir = os.path.join(self.config.UPLOAD_FOLDER, upload_id)
            metadata_path = os.path.join(upload_dir, 'metadata.json')
            
            if not os.path.exists(metadata_path):
                return {'success': False, 'error': 'Document metadata not found'}
            
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"📋 Processing text extraction for upload {upload_id}")
            logger.debug(f"Metadata structure: {list(metadata.keys())}")
            
            text_blocks = []
            pages = metadata.get('pages', [])
            
            if not pages:
                return {'success': False, 'error': 'No pages found in metadata'}
            
            for i, page in enumerate(pages):
                logger.debug(f"Processing page {i}: {list(page.keys())}")
                
                # Handle different possible path keys
                image_path = None
                for path_key in ['path', 'image_path', 'file_path']:
                    if path_key in page:
                        image_path = page[path_key]
                        break
                
                if not image_path:
                    logger.warning(f"⚠️ No path found in page {i}, skipping")
                    continue
                
                page_number = page.get('page_number', page.get('slide_number', i))
                
                if not os.path.exists(image_path):
                    logger.warning(f"⚠️ Image file not found: {image_path}")
                    continue
                
                logger.info(f"🔍 Extracting text from page {page_number}: {image_path}")
                
                page_result = self._extract_text_with_enhanced_ocr(image_path, page_number)
                
                if page_result['success']:
                    extracted_blocks = page_result['text_blocks']
                    text_blocks.extend(extracted_blocks)
                    logger.info(f"✅ Extracted {len(extracted_blocks)} text blocks from page {page_number}")
                else:
                    logger.warning(f"⚠️ OCR failed for page {page_number}: {page_result.get('error', 'Unknown error')}")
            
            # Phase 2: Apply semantic chunking
            if self.chunking_model and text_blocks:
                text_blocks = self._apply_semantic_chunking(text_blocks, upload_id)
            
            # Save extracted text
            text_result = {
                'upload_id': upload_id,
                'extracted_at': str(datetime.now()),
                'total_blocks': len(text_blocks),
                'text_blocks': text_blocks,
                'semantic_chunking_applied': self.chunking_model is not None
            }
            
            result_path = os.path.join(upload_dir, 'extracted_text.json')
            with open(result_path, 'w', encoding='utf-8') as f:
                json.dump(text_result, f, indent=2, ensure_ascii=False)
            
            logger.info(f"🎉 Text extraction completed: {len(text_blocks)} total blocks extracted")
            
            return {
                'success': True,
                'text_blocks': text_blocks,
                'total_blocks': len(text_blocks)
            }
            
        except Exception as e:
            logger.error(f"Text extraction error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _extract_text_with_enhanced_ocr(self, image_path: str, page_number: int) -> Dict[str, Any]:
        """Enhanced OCR with multiple preprocessing techniques"""
        try:
            logger.debug(f"Loading image: {image_path}")
            
            original_image = cv2.imread(image_path)
            if original_image is None:
                try:
                    pil_img = Image.open(image_path)
                    original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
                except Exception as e:
                    return {'success': False, 'error': f'Could not load image: {str(e)}'}
            
            # Create multiple preprocessed versions
            preprocessed_images = self._create_multiple_preprocessed_versions(original_image)
            
            all_results = []
            
            # Extract text from each preprocessed version
            for prep_name, prep_image in preprocessed_images.items():
                try:
                    # Convert back to PIL for tesseract
                    pil_image = Image.fromarray(cv2.cvtColor(prep_image, cv2.COLOR_BGR2RGB))
                    
                    # Multiple OCR configurations
                    ocr_configs = [
                        r'--oem 3 --psm 6',  # Uniform block
                        r'--oem 3 --psm 4',  # Single column
                        r'--oem 3 --psm 3',  # Fully automatic
                    ]
                    
                    for config in ocr_configs:
                        try:
                            data = pytesseract.image_to_data(
                                pil_image,
                                config=config,
                                output_type=pytesseract.Output.DICT
                            )
                            
                            # Extract high-confidence text
                            page_text = self._extract_confident_text(data, prep_name, config)
                            all_results.extend(page_text)
                            
                        except Exception as e:
                            logger.debug(f"OCR config {config} failed for {prep_name}: {e}")
                            continue
                    
                except Exception as e:
                    logger.debug(f"Preprocessing {prep_name} failed: {e}")
                    continue
            
            # Merge and deduplicate results
            final_blocks = self._merge_and_deduplicate_results(all_results, page_number)
            
            logger.info(f"Enhanced OCR extracted {len(final_blocks)} blocks from page {page_number}")
            
            return {
                'success': True,
                'text_blocks': final_blocks,
                'methods_used': list(preprocessed_images.keys())
            }
            
        except Exception as e:
            logger.error(f"Enhanced OCR error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _apply_semantic_chunking(self, text_blocks: List[Dict[str, Any]], upload_id: str) -> List[Dict[str, Any]]:
        """Phase 2: Apply semantic chunking to text blocks"""
        try:
            if not self.chunking_model or len(text_blocks) < 2:
                return text_blocks
            
            logger.info(f"🧠 Applying semantic chunking to {len(text_blocks)} text blocks")
            
            # Group blocks by page for context
            pages = {}
            for block in text_blocks:
                page_num = block.get('page_number', 0)
                if page_num not in pages:
                    pages[page_num] = []
                pages[page_num].append(block)
            
            chunked_blocks = []
            
            # Process each page
            for page_num, page_blocks in pages.items():
                if len(page_blocks) <= 1:
                    chunked_blocks.extend(page_blocks)
                    continue
                
                page_chunks = self._create_semantic_chunks(page_blocks, page_num, upload_id)
                chunked_blocks.extend(page_chunks)
            
            logger.info(f"✅ Semantic chunking: {len(text_blocks)} → {len(chunked_blocks)} chunks")
            return chunked_blocks
            
        except Exception as e:
            logger.error(f"Semantic chunking error: {str(e)}")
            return text_blocks
    
    def _create_semantic_chunks(self, blocks: List[Dict[str, Any]], page_num: int, upload_id: str) -> List[Dict[str, Any]]:
        """Create semantically coherent chunks for a page"""
        try:
            if len(blocks) <= 1:
                return blocks
            
            # Sort blocks by position if bbox is available
            sorted_blocks = sorted(blocks, key=lambda x: (
                x.get('bbox', [0, 0, 0, 0])[1],  # Y position
                x.get('bbox', [0, 0, 0, 0])[0]   # X position
            ))
            
            chunks = []
            current_chunk_text = ""
            current_chunk_blocks = []
            
            for i, block in enumerate(sorted_blocks):
                block_text = block['text']
                
                # Check semantic similarity with current chunk
                if current_chunk_text and len(current_chunk_text) > 50:
                    similarity = self._calculate_semantic_similarity(current_chunk_text, block_text)
                    
                    # If similarity is low or chunk is getting too long, start new chunk
                    if similarity < 0.4 or len(current_chunk_text) > 400:
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
                    # First block or very short current chunk
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
            logger.error(f"Chunk creation error: {str(e)}")
            return blocks
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """Calculate semantic similarity between texts"""
        try:
            if not self.chunking_model:
                return self._calculate_word_overlap(text1, text2)
            
            embeddings = self.chunking_model.encode([text1, text2])
            similarity = np.dot(embeddings[0], embeddings[1]) / (
                np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
            )
            return float(similarity)
            
        except Exception as e:
            logger.debug(f"Semantic similarity calculation failed: {str(e)}")
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
    
    def _create_chunk(self, text: str, metadata_blocks: List[Dict], page_num: int, upload_id: str, chunk_id: int) -> Dict[str, Any]:
        """Create a semantic chunk with combined metadata"""
        # Calculate average confidence
        confidences = [block.get('confidence', 0.5) for block in metadata_blocks]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Merge bounding boxes
        bboxes = [block.get('bbox', [0, 0, 0, 0]) for block in metadata_blocks if 'bbox' in block]
        merged_bbox = self._merge_bounding_boxes(bboxes) if bboxes else [0, 0, 0, 0]
        
        return {
            'text': text.strip(),
            'page_number': page_num,
            'confidence': avg_confidence,
            'bbox': merged_bbox,
            'upload_id': upload_id,
            'chunk_id': chunk_id,
            'chunk_type': 'semantic_boundary',
            'source_blocks': len(metadata_blocks),
            'method': 'semantic_chunking',
            'engines_used': list(set(block.get('method', 'unknown') for block in metadata_blocks))
        }
    
    # Keep all existing methods for backward compatibility
    def _create_multiple_preprocessed_versions(self, image):
        """Create multiple preprocessed versions of the image"""
        versions = {}
        
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            versions['basic_gray'] = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
            
            denoised = cv2.bilateralFilter(gray, 9, 75, 75)
            versions['denoised'] = cv2.cvtColor(denoised, cv2.COLOR_GRAY2BGR)
            
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            versions['enhanced_contrast'] = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)
            
            adaptive_thresh = cv2.adaptiveThreshold(
                enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
            )
            versions['adaptive_thresh'] = cv2.cvtColor(adaptive_thresh, cv2.COLOR_GRAY2BGR)
            
            _, otsu_thresh = cv2.threshold(enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            versions['otsu_thresh'] = cv2.cvtColor(otsu_thresh, cv2.COLOR_GRAY2BGR)
            
            return versions
            
        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            return {'original': image}
    
    def _extract_confident_text(self, ocr_data, method_name, config_name):
        """Extract only high-confidence text from OCR data"""
        text_blocks = []
        
        try:
            current_text = ""
            current_confidences = []
            current_boxes = []
            
            for i in range(len(ocr_data['text'])):
                text = ocr_data['text'][i].strip()
                confidence = int(ocr_data['conf'][i])
                
                if text and confidence > 40:
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
                            avg_confidence = sum(current_confidences) / len(current_confidences)
                            
                            text_blocks.append({
                                'text': cleaned_text,
                                'confidence': avg_confidence / 100.0,
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
                    avg_confidence = sum(current_confidences) / len(current_confidences) if current_confidences else 50
                    
                    text_blocks.append({
                        'text': cleaned_text,
                        'confidence': avg_confidence / 100.0,
                        'bbox': self._merge_bounding_boxes(current_boxes) if current_boxes else [0, 0, 100, 100],
                        'method': f"{method_name}_{config_name}",
                        'word_count': len(cleaned_text.split()),
                        'char_count': len(cleaned_text)
                    })
            
            return text_blocks
            
        except Exception as e:
            logger.error(f"Confident text extraction failed: {e}")
            return []
    
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
    
    def _merge_and_deduplicate_results(self, all_results, page_number):
        """Merge and deduplicate text blocks from multiple methods"""
        if not all_results:
            return []
        
        # Sort by confidence (highest first)
        all_results.sort(key=lambda x: x['confidence'], reverse=True)
        
        final_blocks = []
        used_texts = set()
        
        for block in all_results:
            text = block['text'].lower().strip()
            
            # Skip if we've seen similar text
            is_duplicate = False
            for used_text in used_texts:
                if self._text_similarity(text, used_text) > 0.8:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                block['page_number'] = page_number
                final_blocks.append(block)
                used_texts.add(text)
        
        return final_blocks[:20]  # Top 20 blocks per page
    
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
