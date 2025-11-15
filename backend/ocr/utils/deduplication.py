"""
Spatial Deduplication Utilities
Removes duplicate text regions detected by multiple language models.
"""

import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class SpatialDeduplicator:
    """
    Remove duplicate text regions detected by multiple language models.
    Uses IoU (Intersection over Union) to detect overlapping regions.
    """
    
    @staticmethod
    def deduplicate(
        results: List[Tuple],
        iou_threshold: float = 0.5
    ) -> List[Tuple]:
        """
        Remove duplicate text regions detected by multiple language models.
        
        Args:
            results: List of tuples (text, confidence, bbox, page_number)
            iou_threshold: IoU threshold for considering regions as duplicates (0.0-1.0)
        
        Returns:
            Deduplicated list of tuples
        """
        if len(results) <= 1:
            return results
        
        # Sort by confidence (highest first)
        sorted_results = sorted(results, key=lambda x: x[1], reverse=True)
        
        deduplicated = []
        for item in sorted_results:
            text, confidence, bbox, page_num = item
            
            # Check if this region overlaps significantly with any already added
            is_duplicate = False
            for existing_item in deduplicated:
                existing_text, existing_conf, existing_bbox, existing_page = existing_item
                
                # Only compare regions on the same page
                if page_num != existing_page:
                    continue
                
                # Skip if either bbox is None
                if bbox is None or existing_bbox is None:
                    continue
                
                # Calculate IoU
                iou = SpatialDeduplicator._calculate_iou(bbox, existing_bbox)
                
                if iou > iou_threshold:
                    # Duplicate detected - keep the one with higher confidence
                    # (already sorted by confidence, so existing one wins)
                    is_duplicate = True
                    logger.debug(
                        f"Duplicate detected: '{text}' (conf={confidence:.2f}) "
                        f"overlaps with '{existing_text}' (conf={existing_conf:.2f}), "
                        f"IoU={iou:.2f}"
                    )
                    break
            
            if not is_duplicate:
                deduplicated.append(item)
        
        logger.info(
            f"Deduplication: {len(results)} regions -> {len(deduplicated)} regions "
            f"({len(results) - len(deduplicated)} duplicates removed)"
        )
        
        return deduplicated
    
    @staticmethod
    def _calculate_iou(bbox1: List[int], bbox2: List[int]) -> float:
        """
        Calculate Intersection over Union (IoU) between two bounding boxes.
        
        Args:
            bbox1: [x, y, width, height]
            bbox2: [x, y, width, height]
        
        Returns:
            IoU value (0.0-1.0)
        """
        try:
            x1, y1, w1, h1 = bbox1
            x2, y2, w2, h2 = bbox2
            
            # Calculate intersection rectangle
            x_left = max(x1, x2)
            y_top = max(y1, y2)
            x_right = min(x1 + w1, x2 + w2)
            y_bottom = min(y1 + h1, y2 + h2)
            
            # No intersection
            if x_right < x_left or y_bottom < y_top:
                return 0.0
            
            # Calculate intersection area
            intersection_area = (x_right - x_left) * (y_bottom - y_top)
            
            # Calculate union area
            bbox1_area = w1 * h1
            bbox2_area = w2 * h2
            union_area = bbox1_area + bbox2_area - intersection_area
            
            # Avoid division by zero
            if union_area == 0:
                return 0.0
            
            return intersection_area / union_area
        
        except (TypeError, ValueError, ZeroDivisionError):
            return 0.0
