"""
PaddleOCR Result Parsing Utilities
Handles PaddleOCR output format variations and bounding box normalization.
"""

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class PaddleOCRParser:
    """
    Parser for PaddleOCR results.
    
    Handles both classic and newer output formats:
    - Classic: [[bbox, (text, score)], ...]
    - Newer: [{'rec_texts': [...], 'rec_scores': [...], 'boxes': [...]}, ...]
    """
    
    @staticmethod
    def parse_result(result: List) -> List[Tuple[str, float, Optional[List[int]]]]:
        """
        Parse PaddleOCR result format into standardized (text, confidence, bbox) tuples.
        
        Args:
            result: Raw PaddleOCR output
        
        Returns:
            List of (text, confidence, bbox) tuples where bbox is [x, y, width, height] or None
        """
        parsed_results = []
        
        if not result or not isinstance(result, list):
            return parsed_results
        
        # Handle multi-page results (result[0] is first page)
        for page_result in result:
            if not page_result:
                continue
            
            # Newer format: dict with 'rec_texts', 'rec_scores', 'boxes'
            if isinstance(page_result, dict):
                texts = page_result.get('rec_texts', [])
                scores = page_result.get('rec_scores', [])
                boxes = page_result.get('boxes', [])
                
                for i, text in enumerate(texts):
                    confidence = scores[i] if i < len(scores) else 0.0
                    bbox_coords = boxes[i] if i < len(boxes) else None
                    bbox = PaddleOCRParser.normalize_bbox(bbox_coords)
                    parsed_results.append((text, confidence, bbox))
            
            # Classic format: list of [bbox, (text, score)]
            elif isinstance(page_result, list):
                for item in page_result:
                    if not isinstance(item, (list, tuple)):
                        continue
                    
                    # Format: [bbox, (text, score)]
                    if len(item) >= 2:
                        bbox_coords = item[0]
                        text_data = item[1]
                        
                        if isinstance(text_data, (list, tuple)) and len(text_data) >= 2:
                            text = text_data[0]
                            confidence = text_data[1]
                            bbox = PaddleOCRParser.normalize_bbox(bbox_coords)
                            parsed_results.append((text, confidence, bbox))
                        elif isinstance(text_data, str):
                            # Sometimes text_data is just a string (no confidence)
                            text = text_data
                            confidence = 1.0  # Default confidence
                            bbox = PaddleOCRParser.normalize_bbox(bbox_coords)
                            parsed_results.append((text, confidence, bbox))
        
        return parsed_results
    
    @staticmethod
    def normalize_bbox(bbox_coords) -> Optional[List[int]]:
        """
        Normalize bounding box coordinates to [x, y, width, height] format.
        PaddleOCR returns [[x1,y1], [x2,y2], [x3,y3], [x4,y4]] (rotated rectangle).
        
        Args:
            bbox_coords: Raw bounding box coordinates from PaddleOCR
        
        Returns:
            [x, y, width, height] or None if invalid
        """
        if not bbox_coords or not isinstance(bbox_coords, (list, tuple)):
            return None
        
        try:
            # Flatten nested structure: [[x1,y1], [x2,y2], ...] -> [x1,y1,x2,y2,...]
            if isinstance(bbox_coords[0], (list, tuple)):
                coords = []
                for point in bbox_coords:
                    coords.extend(point[:2])  # Take x, y from each point
                bbox_coords = coords
            
            # Extract all x and y coordinates
            x_coords = [bbox_coords[i] for i in range(0, len(bbox_coords), 2)]
            y_coords = [bbox_coords[i] for i in range(1, len(bbox_coords), 2)]
            
            # Calculate bounding rectangle
            x = int(min(x_coords))
            y = int(min(y_coords))
            width = int(max(x_coords) - x)
            height = int(max(y_coords) - y)
            
            return [x, y, width, height]
        
        except (IndexError, TypeError, ValueError):
            return None
