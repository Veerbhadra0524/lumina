import os
import uuid
import fitz  # PyMuPDF
from pptx import Presentation
from PIL import Image
import logging
from typing import Dict, Any, Optional
from werkzeug.datastructures import FileStorage
from datetime import datetime
import json

from config import Config

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """Handles document upload and initial processing"""
    
    def __init__(self):
        self.config = Config()
    
    def generate_upload_id(self) -> str:
        """Generate unique upload ID"""
        return str(uuid.uuid4())[:8]
    
    def validate_file(self, file: FileStorage) -> bool:
        """Validate uploaded file"""
        if not file.filename:
            return False
        
        # Check extension
        ext = '.' + file.filename.rsplit('.', 1)[-1].lower()
        if ext not in self.config.ALLOWED_EXTENSIONS:
            return False
        
        # Check file size (approximate)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)  # Reset
        
        return size <= self.config.MAX_CONTENT_LENGTH
    
    def process_document(self, file: FileStorage, upload_id: str) -> Dict[str, Any]:
        """Process uploaded document and extract pages"""
        try:
            # Create upload directory
            upload_dir = os.path.join(self.config.UPLOAD_FOLDER, upload_id)
            os.makedirs(upload_dir, exist_ok=True)
            
            # Create pages subdirectory
            pages_dir = os.path.join(upload_dir, 'pages')
            os.makedirs(pages_dir, exist_ok=True)
            
            # Save original file
            filename = file.filename
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Determine file type and process
            ext = '.' + filename.rsplit('.', 1)[-1].lower()
            
            if ext == '.pdf':
                result = self._process_pdf(file_path, pages_dir)
            elif ext == '.pptx':
                result = self._process_pptx(file_path, pages_dir)
            elif ext in ['.png', '.jpg', '.jpeg']:
                result = self._process_image(file_path, pages_dir)
            else:
                return {'success': False, 'error': 'Unsupported file type'}
            
            if result['success']:
                # Create proper metadata structure
                metadata = {
                    'upload_id': upload_id,
                    'filename': filename,
                    'file_type': ext,
                    'page_count': result.get('page_count', 0),
                    'pages': result['pages'],  # This contains the path info
                    'processed_at': datetime.now().isoformat(),
                    'status': 'processed'
                }
                
                # Save metadata
                metadata_path = os.path.join(upload_dir, 'metadata.json')
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                
                logger.info(f"SUCCESS: Document processed: {filename} -> {len(result['pages'])} pages")
            
            return result
            
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _process_pdf(self, file_path: str, pages_dir: str) -> Dict[str, Any]:
        """Process PDF file"""
        try:
            doc = fitz.open(file_path)
            pages = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Convert to image
                mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better quality
                pix = page.get_pixmap(matrix=mat)
                
                # Save as PNG with proper path structure
                img_filename = f'page_{page_num}.png'
                img_path = os.path.join(pages_dir, img_filename)
                pix.save(img_path)
                
                pages.append({
                    'page_number': page_num,
                    'path': img_path,  # ✅ CORRECT: Full path to the image
                    'filename': img_filename,
                    'width': pix.width,
                    'height': pix.height,
                    'type': 'pdf_page'
                })
                
                logger.debug(f"Processed PDF page {page_num} -> {img_path}")
            
            doc.close()
            return {
                'success': True, 
                'pages': pages, 
                'page_count': len(pages),
                'document_type': 'pdf'
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed: {str(e)}")
            return {'success': False, 'error': f'PDF processing failed: {str(e)}'}
    
    def _process_pptx(self, file_path: str, pages_dir: str) -> Dict[str, Any]:
        """Process PowerPoint file"""
        try:
            prs = Presentation(file_path)
            pages = []
            
            for slide_num, slide in enumerate(prs.slides):
                # Create a simple image representation
                img_filename = f'slide_{slide_num}.png'
                img_path = os.path.join(pages_dir, img_filename)
                
                # Create a placeholder image (basic implementation)
                img = Image.new('RGB', (800, 600), 'white')
                img.save(img_path)
                
                pages.append({
                    'slide_number': slide_num,
                    'page_number': slide_num,  # Consistency with PDF
                    'path': img_path,  # ✅ CORRECT: Full path to the image
                    'filename': img_filename,
                    'width': 800,
                    'height': 600,
                    'type': 'pptx_slide'
                })
                
                logger.debug(f"Processed PPTX slide {slide_num} -> {img_path}")
            
            return {
                'success': True, 
                'pages': pages, 
                'page_count': len(pages),
                'document_type': 'pptx'
            }
            
        except Exception as e:
            logger.error(f"PPTX processing failed: {str(e)}")
            return {'success': False, 'error': f'PPTX processing failed: {str(e)}'}
    
    def _process_image(self, file_path: str, pages_dir: str) -> Dict[str, Any]:
        """Process single image file"""
        try:
            # Open and validate image
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = (1600, 1600)
                img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save processed image
                img_filename = 'image_0.png'
                img_path = os.path.join(pages_dir, img_filename)
                img.save(img_path)
                
                pages = [{
                    'page_number': 0,
                    'path': img_path,  # ✅ CORRECT: Full path to the image
                    'filename': img_filename,
                    'width': img.width,
                    'height': img.height,
                    'type': 'single_image'
                }]
                
                logger.debug(f"Processed image -> {img_path}")
                
                return {
                    'success': True,
                    'pages': pages,
                    'page_count': 1,
                    'document_type': 'image'
                }
                
        except Exception as e:
            logger.error(f"Image processing failed: {str(e)}")
            return {'success': False, 'error': f'Image processing failed: {str(e)}'}
