"""
License Plate Reader — extracts plate text from a vehicle snapshot.
Uses EasyOCR for text recognition on the cropped vehicle image.
Falls back gracefully if EasyOCR is not installed or detection fails.
"""

import cv2
import numpy as np
import re

# Lazy-load EasyOCR reader (heavy model, load once)
_reader = None

def _get_reader():
    global _reader
    if _reader is None:
        try:
            import easyocr
            _reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        except ImportError:
            print("[PlateReader] easyocr not installed. Run: pip install easyocr")
            return None
        except Exception as e:
            print(f"[PlateReader] Failed to init EasyOCR: {e}")
            return None
    return _reader


def _clean_plate_text(raw_text):
    """
    Clean OCR output to look like Indian license plates.
    Indian plates: XX 00 XX 0000  (e.g., KA 01 AB 1234)
    Keep only uppercase letters and digits; strip noise.
    """
    # Remove all characters except letters and digits
    cleaned = re.sub(r'[^A-Z0-9]', '', raw_text.upper())
    
    # Accept anything 3-15 chars — flexible enough for various plate formats or partial reads
    if 3 <= len(cleaned) <= 15:
        return cleaned
    return None


def extract_plate(car_image):
    """
    Attempt to extract a license plate number from a cropped vehicle image.
    
    Args:
        car_image: numpy array (BGR) of the cropped vehicle
        
    Returns:
        str: detected plate text, or None if not detected
    """
    if car_image is None or car_image.size == 0:
        return None
    
    reader = _get_reader()
    if reader is None:
        return None
    
    try:
        # Upscale the image to give EasyOCR more pixels to work with on small crops
        height, width = car_image.shape[:2]
        if width < 500:
            scale = 2.0
            car_image = cv2.resize(car_image, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        
        # EasyOCR often performs better on the raw RGB image than on custom grayscaled versions, 
        # as it applies its own internal binarization and contrast adjustments.
        results = reader.readtext(car_image, detail=1, paragraph=False, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
        
        # Fallback to enhanced grayscale if nothing found
        if not results:
            gray = cv2.cvtColor(car_image, cv2.COLOR_BGR2GRAY)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            results = reader.readtext(enhanced, detail=1, paragraph=False, allowlist='ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
            
        if not results:
            return None
        
        # Filter results: look for plate-like text (letters + digits mix)
        candidates = []
        for (bbox, text, confidence) in results:
            if confidence < 0.3:  # Skip very low confidence
                continue
            cleaned = _clean_plate_text(text)
            if cleaned:
                candidates.append((cleaned, confidence))
        
        if not candidates:
            return None
        
        # Return the highest confidence match
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]
        
    except Exception as e:
        # Never crash the pipeline for OCR failures
        return None
