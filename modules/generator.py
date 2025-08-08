import logging
import requests
from typing import Dict, Any, List, Optional
import json
import os
import re
import google.generativeai as genai
from PIL import Image
import io
import base64

from config import Config

logger = logging.getLogger(__name__)

class Generator:
    """Enhanced generator with Gemini API and vision capabilities"""
    
    def __init__(self):
        self.config = Config()
        self.gemini_model = None
        self.vision_model = None
        self._initialize_gemini()
    
    def _initialize_gemini(self):
        """Initialize Gemini API"""
        try:
            if self.config.GEMINI_API_KEY:
                genai.configure(api_key=self.config.GEMINI_API_KEY)
                
                # Initialize text model
                self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
                
                # Initialize vision model  
                self.vision_model = genai.GenerativeModel('gemini-1.5-flash')
                
                logger.info(f"SUCCESS: Gemini API initialized successfully")
            else:
                logger.warning(f"WARNING: No Gemini API key found")
                
        except Exception as e:
            logger.error(f"ERROR: Gemini initialization failed: {e}")
    
    def generate_answer(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer with enhanced context understanding"""
        try:
            if not documents:
                return {
                    'success': True,
                    'answer': "I don't have any relevant information to answer this question. Please upload some documents first.",
                    'confidence': 0.1
                }
            
            # Prepare enhanced context
            context = self._prepare_enhanced_context(documents)
            
            # Try different generation methods in order
            # 1. Gemini API (preferred)
            if self.config.GEMINI_API_KEY and self.gemini_model:
                try:
                    result = self._generate_with_gemini(query, context, documents)
                    if result['success']:
                        return result
                except Exception as e:
                    logger.warning(f"Gemini failed: {e}")
            
            # 2. Local LLM fallback
            if self.config.USE_LOCAL_LLM:
                try:
                    result = self._generate_with_local_llm(query, context)
                    if result['success']:
                        return result
                except Exception as e:
                    logger.warning(f"Local LLM failed: {e}")
            
            # 3. Enhanced template generation
            return self._generate_enhanced_template_answer(query, documents, context)
            
        except Exception as e:
            logger.error(f"Answer generation error: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def _prepare_enhanced_context(self, documents: List[Dict[str, Any]]) -> str:
        """Prepare rich context with metadata"""
        try:
            context_parts = []
            image_references = []
            
            for i, doc in enumerate(documents[:5]):
                text = doc.get('text', '')
                page = doc.get('page_number', 'unknown')
                confidence = doc.get('confidence', 0)
                upload_id = doc.get('upload_id', '')
                
                if text and len(text.strip()) > 10:
                    # Clean and enhance text
                    clean_text = self._enhance_text_for_context(text)
                    
                    # Add metadata enrichment
                    context_parts.append(
                        f"[Document {i+1} - Page {page} - Confidence: {confidence:.2f}]\n{clean_text}\n"
                    )
                    
                    # Check for image references
                    if upload_id:
                        image_path = self._get_page_image_path(upload_id, page)
                        if image_path and os.path.exists(image_path):
                            image_references.append({
                                'page': page,
                                'path': image_path,
                                'context': clean_text[:100]
                            })
            
            context = "\n".join(context_parts)
            
            # Add image context if available
            if image_references:
                context += f"\n\n[VISUAL CONTENT AVAILABLE]\n"
                for img_ref in image_references[:3]:
                    context += f"- Page {img_ref['page']}: Contains visual elements related to '{img_ref['context']}...'\n"
            
            return context
            
        except Exception as e:
            logger.error(f"Context preparation error: {str(e)}")
            return ""
    
    def _enhance_text_for_context(self, text: str) -> str:
        """Enhanced text processing for better context"""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Fix common OCR errors
        ocr_fixes = {
            r'\b1\b': 'I',  # Common OCR mistake
            r'\b0\b': 'O',  # Another common mistake
            r'(\w)\s+(\w)(?=\s|$)': r'\1\2',  # Fix spaced letters
        }
        
        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text)
        
        # Truncate smartly at sentence boundaries
        if len(text) > 400:
            sentences = text.split('. ')
            truncated = '. '.join(sentences[:3])
            if len(truncated) < len(text):
                truncated += '.'
            return truncated
        
        return text
    
    def _get_page_image_path(self, upload_id: str, page_number: int) -> Optional[str]:
        """Get image path for a specific page"""
        try:
            possible_paths = [
                os.path.join(self.config.UPLOAD_FOLDER, upload_id, 'pages', f'page_{page_number}.png'),
                os.path.join(self.config.UPLOAD_FOLDER, upload_id, 'pages', f'slide_{page_number}.png'),
                os.path.join(self.config.UPLOAD_FOLDER, upload_id, 'pages', 'image_0.png'),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    return path
            return None
            
        except Exception as e:
            logger.error(f"Image path resolution error: {e}")
            return None
    
    def _generate_with_gemini(self, query: str, context: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer using Gemini API with vision support"""
        try:
            # Check if we have images to analyze
            image_docs = [doc for doc in documents if self._get_page_image_path(
                doc.get('upload_id', ''), doc.get('page_number', 0)
            )]
            
            if image_docs and len(image_docs) > 0:
                return self._generate_multimodal_with_gemini(query, context, image_docs)
            else:
                return self._generate_text_only_with_gemini(query, context)
                
        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_text_only_with_gemini(self, query: str, context: str) -> Dict[str, Any]:
        """Generate text-only response with Gemini"""
        try:
            prompt = f"""You are a document analysis assistant. Based on the provided context from uploaded documents, answer the question accurately and comprehensively.

DOCUMENT CONTEXT:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Use ONLY the information from the provided context
2. Be specific and mention page numbers when referencing information
3. If the context doesn't fully answer the question, acknowledge the limitation
4. Provide a well-structured, informative response
5. Highlight key details and relationships between information

RESPONSE:"""

            response = self.gemini_model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=300,
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            if response and response.text:
                answer = response.text.strip()
                return {
                    'success': True,
                    'answer': answer,
                    'confidence': 0.85,
                    'method': 'gemini_text'
                }
            else:
                return {'success': False, 'error': 'Empty response from Gemini'}
                
        except Exception as e:
            logger.error(f"Gemini text generation failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _generate_multimodal_with_gemini(self, query: str, context: str, image_docs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate response with text + image analysis using Gemini Vision"""
        try:
            # Prepare images for analysis
            images = []
            image_contexts = []
            
            for doc in image_docs[:3]:  # Limit to 3 images for API limits
                image_path = self._get_page_image_path(
                    doc.get('upload_id', ''), 
                    doc.get('page_number', 0)
                )
                
                if image_path and os.path.exists(image_path):
                    try:
                        pil_image = Image.open(image_path)
                        images.append(pil_image)
                        image_contexts.append(f"Page {doc.get('page_number', 'unknown')}")
                    except Exception as e:
                        logger.warning(f"Failed to load image {image_path}: {e}")
            
            if not images:
                # Fallback to text-only if no images could be loaded
                return self._generate_text_only_with_gemini(query, context)
            
            # Create multimodal prompt
            prompt_parts = [
                f"""You are an advanced document analysis assistant with vision capabilities. Analyze both the text context and the provided images to answer the question comprehensively.

TEXT CONTEXT FROM DOCUMENTS:
{context}

USER QUESTION: {query}

INSTRUCTIONS:
1. Analyze BOTH the text context and the visual content in the images
2. Provide insights that combine textual and visual information
3. Mention specific page numbers when referencing information
4. If images contain additional details not in the text, include them
5. Be specific about what you can see in the images
6. Provide a comprehensive, well-structured response

RESPONSE:"""
            ]
            
            # Add images to the prompt
            for i, (image, img_context) in enumerate(zip(images, image_contexts)):
                prompt_parts.append(f"\nImage {i+1} ({img_context}):")
                prompt_parts.append(image)
            
            response = self.vision_model.generate_content(
                prompt_parts,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=400,
                    temperature=0.3,
                    top_p=0.8,
                    top_k=40
                )
            )
            
            if response and response.text:
                answer = response.text.strip()
                return {
                    'success': True,
                    'answer': answer,
                    'confidence': 0.9,  # Higher confidence for multimodal
                    'method': 'gemini_vision',
                    'images_analyzed': len(images)
                }
            else:
                return {'success': False, 'error': 'Empty response from Gemini Vision'}
                
        except Exception as e:
            logger.error(f"Gemini vision generation failed: {e}")
            # Fallback to text-only
            return self._generate_text_only_with_gemini(query, context)
    
    def _generate_with_local_llm(self, query: str, context: str) -> Dict[str, Any]:
        """Generate with local LLM (Ollama)"""
        try:
            url = f"{self.config.OLLAMA_BASE_URL}/api/generate"
            
            prompt = f"""Based on the document context below, answer the question comprehensively.

Context:
{context}

Question: {query}

Answer (be detailed and accurate):"""
            
            data = {
                "model": self.config.LOCAL_MODEL_NAME,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            }
            
            response = requests.post(url, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('response', '').strip()
                
                return {
                    'success': True,
                    'answer': answer,
                    'confidence': 0.7,
                    'method': 'local_llm'
                }
            else:
                return {'success': False, 'error': f"Local LLM error: {response.status_code}"}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _generate_enhanced_template_answer(self, query: str, documents: List[Dict[str, Any]], context: str) -> Dict[str, Any]:
        """Enhanced template-based answer with better context utilization"""
        try:
            # Extract high-confidence information
            high_conf_docs = [doc for doc in documents if doc.get('confidence', 0) > 0.4]
            
            if high_conf_docs:
                # Create structured answer from high-confidence documents
                answer_parts = []
                pages_found = set()
                
                for doc in high_conf_docs[:3]:
                    text = doc.get('text', '')
                    page = doc.get('page_number', 'unknown')
                    confidence = doc.get('confidence', 0)
                    
                    if text and len(text.strip()) > 20:
                        # Extract most relevant sentence
                        relevant_text = self._extract_most_relevant_text(query, text)
                        if relevant_text:
                            answer_parts.append(f"From page {page} (confidence: {confidence:.1f}): {relevant_text}")
                            pages_found.add(str(page))
                
                if answer_parts:
                    answer = "Based on your documents:\n\n" + "\n\n".join(answer_parts)
                    
                    if len(pages_found) > 1:
                        answer += f"\n\n📄 Information found across pages: {', '.join(sorted(pages_found))}"
                    
                    confidence = min(0.7, max(doc['confidence'] for doc in high_conf_docs))
                else:
                    answer = self._create_fallback_answer(query, documents)
                    confidence = 0.3
            else:
                answer = self._create_fallback_answer(query, documents)
                confidence = 0.2
            
            return {
                'success': True,
                'answer': answer,
                'confidence': confidence,
                'method': 'enhanced_template'
            }
            
        except Exception as e:
            logger.error(f"Template generation error: {e}")
            return {
                'success': True,
                'answer': "I found some relevant information in your documents, but had trouble processing it. Please try rephrasing your question.",
                'confidence': 0.2,
                'method': 'fallback'
            }
    
    def _extract_most_relevant_text(self, query: str, text: str) -> str:
        """Extract most relevant part of text for the query"""
        try:
            query_words = set(query.lower().split())
            sentences = text.split('. ')
            
            best_sentence = ""
            best_score = 0
            
            for sentence in sentences:
                if len(sentence.strip()) < 15:
                    continue
                
                sentence_words = set(sentence.lower().split())
                # Calculate relevance score
                overlap = len(query_words.intersection(sentence_words))
                score = overlap / len(query_words) if query_words else 0
                
                # Boost score for complete phrases
                if any(word in sentence.lower() for word in query.lower().split() if len(word) > 3):
                    score += 0.2
                
                if score > best_score:
                    best_score = score
                    best_sentence = sentence.strip()
            
            return best_sentence if best_score > 0.1 else text[:150] + "..."
            
        except Exception as e:
            return text[:150] + "..."
    
    def _create_fallback_answer(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """Create fallback answer when confidence is low"""
        pages = set()
        for doc in documents:
            page = doc.get('page_number')
            if page is not None:
                pages.add(str(page))
        
        if pages:
            pages_list = sorted([p for p in pages if p != 'unknown'])
            if pages_list:
                return f"I found some information related to your question on page(s) {', '.join(pages_list)}, but the text quality is low due to OCR limitations. Consider re-uploading clearer document images for better analysis."
        
        return "The document contains some relevant information, but I need better quality text to provide a specific answer. Please try uploading clearer images or documents."


# Create generator instance
generator = Generator()
