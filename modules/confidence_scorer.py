import numpy as np
from typing import Dict, Any, List

class AdvancedConfidenceScorer:
    """Multi-factor confidence scoring for better result ranking"""
    
    def calculate_enhanced_confidence(self, 
                                    text_block: Dict[str, Any], 
                                    retrieval_score: float, 
                                    context: Dict[str, Any]) -> float:
        """Calculate confidence using multiple weighted factors"""
        
        factors = {
            'ocr_confidence': text_block.get('confidence', 0.5),
            'text_length': min(len(text_block.get('text', '')) / 100, 1.0),
            'retrieval_score': retrieval_score,
            'context_coherence': self._calculate_context_coherence(text_block, context),
            'cross_validation': self._cross_validate_with_other_sources(text_block, context),
            'entity_recognition': self._calculate_entity_confidence(text_block.get('text', '')),
            'engine_consensus': self._calculate_engine_consensus(text_block)
        }
        
        # Weighted combination (research-backed weights)
        weights = {
            'ocr_confidence': 0.25,
            'text_length': 0.05,
            'retrieval_score': 0.30,
            'context_coherence': 0.15,
            'cross_validation': 0.10,
            'entity_recognition': 0.10,
            'engine_consensus': 0.05
        }
        
        final_confidence = sum(factors[factor] * weights[factor] for factor in factors)
        
        # Ensure confidence is within bounds
        return min(0.95, max(0.05, final_confidence))
    
    def _calculate_context_coherence(self, text_block: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Calculate how well the text fits within the document context"""
        # Simplified coherence calculation
        text = text_block.get('text', '').lower()
        
        # Check for common document terms
        doc_terms = context.get('common_terms', [])
        if doc_terms:
            term_overlap = sum(1 for term in doc_terms if term in text)
            coherence = min(1.0, term_overlap / len(doc_terms))
        else:
            coherence = 0.5  # Neutral if no context
        
        return coherence
    
    def _cross_validate_with_other_sources(self, text_block: Dict[str, Any], context: Dict[str, Any]) -> float:
        """Cross-validate information with other sources in the document"""
        # Simplified cross-validation
        text = text_block.get('text', '').lower()
        other_blocks = context.get('other_text_blocks', [])
        
        if not other_blocks:
            return 0.5
        
        # Check for similar information in other blocks
        matches = 0
        for other_block in other_blocks[:5]:  # Check top 5 similar blocks
            other_text = other_block.get('text', '').lower()
            if self._text_overlap(text, other_text) > 0.3:
                matches += 1
        
        return min(1.0, matches / 3)  # Normalize to 0-1
    
    def _calculate_entity_confidence(self, text: str) -> float:
        """Calculate confidence based on named entity recognition"""
        # Simplified entity recognition confidence
        import re
        
        # Look for common entity patterns
        patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Person names
            r'\b\d{4}\b',  # Years
            r'\b[A-Z][a-zA-Z\s]+(?:Inc|Ltd|Corp|Company)\b',  # Company names
            r'\b\d+(?:\.\d+)?%\b',  # Percentages
        ]
        
        entity_count = 0
        for pattern in patterns:
            entity_count += len(re.findall(pattern, text))
        
        # More entities generally indicate structured, reliable text
        return min(1.0, entity_count / max(1, len(text.split()) / 10))
    
    def _calculate_engine_consensus(self, text_block: Dict[str, Any]) -> float:
        """Calculate confidence boost if multiple OCR engines agree"""
        consensus_engines = text_block.get('consensus_engines', 1)
        if consensus_engines > 1:
            return min(1.0, 0.5 + (consensus_engines - 1) * 0.2)
        return 0.5
    
    def _text_overlap(self, text1: str, text2: str) -> float:
        """Calculate word overlap between two texts"""
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        return len(intersection) / len(union)
