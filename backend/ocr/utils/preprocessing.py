"""
Image Preprocessing Utilities
Supports: denoising, deskewing, contrast enhancement, sharpening
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    cv2 = None
    np = None
    _HAS_CV2 = False


class ImagePreprocessor:
    """
    Image preprocessing pipeline for OCR quality improvement.
    
    Features:
    - Denoising (bilateral filter)
    - Deskewing (rotation correction)
    - Contrast enhancement (CLAHE)
    - Sharpening (unsharp mask)
    """
    
    def __init__(
        self,
        do_denoise: bool = True,
        do_deskew: bool = True,
        do_contrast: bool = True,
        do_sharpen: bool = True
    ):
        """
        Initialize preprocessor with step toggles.
        
        Args:
            do_denoise: Enable denoising
            do_deskew: Enable deskew correction
            do_contrast: Enable contrast enhancement
            do_sharpen: Enable sharpening
        """
        if not _HAS_CV2:
            raise ImportError(
                "OpenCV (cv2) is required for image preprocessing. "
                "Install with: pip install opencv-python"
            )
        
        self.do_denoise = do_denoise
        self.do_deskew = do_deskew
        self.do_contrast = do_contrast
        self.do_sharpen = do_sharpen
    
    def preprocess_image(self, image_path: str) -> str:
        """
        Run preprocessing pipeline: denoise, deskew, contrast enhancement, sharpen.
        
        Args:
            image_path: Path to input image
        
        Returns:
            Path to preprocessed temporary image file
        
        Raises:
            FileNotFoundError: If image_path doesn't exist
            ImportError: If cv2 not available
        """
        try:
            # Read image
            img = cv2.imread(image_path) # type: ignore
            if img is None:
                raise ValueError(f"Failed to read image: {image_path}")
            
            # Apply preprocessing steps
            if self.do_denoise:
                img = self._denoise(img)
            
            if self.do_deskew:
                img = self._deskew(img)
            
            if self.do_contrast:
                img = self._enhance_contrast(img)
            
            if self.do_sharpen:
                img = self._sharpen(img)
            
            # Save to temporary file
            suffix = Path(image_path).suffix or '.jpg'
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                mode='wb'
            )
            temp_path = temp_file.name
            temp_file.close()
            
            cv2.imwrite(temp_path, img)  # type: ignore
            logger.info(f"Preprocessed image saved to: {temp_path}")
            return temp_path

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}")
            # Return original path on failure
            return image_path
    
    def _denoise(self, img):
        """Apply bilateral filter to reduce noise while preserving edges."""
        logger.debug("Applying denoising...")
        return cv2.bilateralFilter(img, d=9, sigmaColor=75, sigmaSpace=75)  # type: ignore
    
    def _deskew(self, img):
        """Detect and correct image rotation/skew."""
        logger.debug("Applying deskew...")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img  # type: ignore
        
        # Detect edges
        edges = cv2.Canny(gray, 50, 150, apertureSize=3)  # type: ignore
        
        # Detect lines using Hough transform
        lines = cv2.HoughLines(edges, 1, np.pi / 180, 200)  # type: ignore
        
        if lines is None or len(lines) == 0:
            return img  # No lines detected, skip deskew
        
        # Calculate dominant angle
        angles = []
        for line in lines[:50]:  # Sample first 50 lines
            rho, theta = line[0]
            angle = np.degrees(theta) - 90  # type: ignore
            angles.append(angle)
        
        median_angle = np.median(angles)  # type: ignore
        
        # Skip if angle is too small (already straight)
        if abs(median_angle) < 0.5:
            return img
        
        # Rotate image
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, float(median_angle), 1.0)  # type: ignore), 1.0)  # type: ignore
        rotated = cv2.warpAffine(  # type: ignore
            img, M, (w, h),
            flags=cv2.INTER_CUBIC,  # type: ignore
            borderMode=cv2.BORDER_REPLICATE  # type: ignore
        )
        
        logger.debug(f"Deskewed by {median_angle:.2f} degrees")
        return rotated
    
    def _enhance_contrast(self, img):
        """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
        logger.debug("Applying contrast enhancement...")
        
        # Convert to LAB color space
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)  # type: ignore
        l, a, b = cv2.split(lab)  # type: ignore
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))  # type: ignore
        l_enhanced = clahe.apply(l)  # type: ignore
        
        # Merge channels
        enhanced_lab = cv2.merge([l_enhanced, a, b])  # type: ignore
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)  # type: ignore
        
        return enhanced
    
    def _sharpen(self, img):
        """Apply unsharp mask for sharpening."""
        logger.debug("Applying sharpening...")
        
        # Create Gaussian blur
        gaussian = cv2.GaussianBlur(img, (0, 0), 2.0)  # type: ignore
        
        # Unsharp mask: img + alpha * (img - blur)
        alpha = 1.5
        sharpened = cv2.addWeighted(img, 1.0 + alpha, gaussian, -alpha, 0)  # type: ignore
        
        return sharpened
